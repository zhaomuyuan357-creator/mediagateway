"""Video analysis service - viral video analysis + storyboard generation.

This extends the storyboard_analyzer with viral video analysis capabilities
based on the 22-dimension video ad analysis framework.
"""
import asyncio
import base64
import json
import logging
import shutil
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

from openai import AsyncOpenAI

from ..config import get_settings
from ..services.provider_router import resolve_provider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class ViralDimension:
    """A single analysis dimension for viral video analysis."""

    dimension: str  # e.g., "内容结构"
    analysis: str  # Detailed analysis in Chinese

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StoryboardShot:
    """A single storyboard shot."""

    shot_id: int
    description_cn: str
    camera_movement: str
    duration: int
    key_elements: str
    seedance_prompt: str
    keyframe_url: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VideoAnalysisResult:
    """Complete video analysis result with viral analysis and storyboard."""

    analysis_id: str
    video_url: Optional[str]
    intent: str
    viral_analysis: List[ViralDimension] = field(default_factory=list)
    storyboard: List[StoryboardShot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "video_url": self.video_url,
            "intent": self.intent,
            "viral_analysis": [v.to_dict() for v in self.viral_analysis],
            "storyboard": [s.to_dict() for s in self.storyboard],
        }


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的电商视频分析师和AI视频分镜师。

用户会上传一个视频或提供视频URL，并说明他们的意图（如"帮我做一个相似的爆款视频"、"分析这个视频的成功因素"等）。

你的任务分为两部分：

## 第一部分：爆款视频分析
基于视频广告素材全景分析体系，从以下6个核心维度分析视频：

1. **内容结构**：分析视频使用的叙事模型（AIDA/PAS/FAB等），黄金3秒开头设计，转场设计
2. **情绪触点**：情绪光谱分析，情绪转折设计，情绪密度
3. **卖点呈现**：功能卖点 vs 情境卖点，卖点排序逻辑
4. **话术类型**：使用的说服策略（理性/感性/恐惧/社交/价值观）
5. **节奏与信息密度**：信息节奏图，关键分析指标
6. **转化优化**：转化路径分析，促单话术模式

## 第二部分：分镜拆解
将视频拆解为多个分镜头，每个分镜包含：
1. 画面描述（中文，详细描述画面内容和动作）
2. 运镜方式（推/拉/摇/移/跟/升/降/固定/环绕）
3. 时长建议（2-5秒）
4. 关键元素（主体产品、背景环境、光线、色调）
5. Seedance英文prompt（适合AI视频生成引擎的英文描述）

请严格输出JSON格式：
{
  "viral_analysis": [
    {"dimension": "维度名称", "analysis": "详细分析内容"}
  ],
  "storyboard": [
    {
      "shot_id": 1,
      "description_cn": "画面中文描述",
      "camera_movement": "运镜方式",
      "duration": 3,
      "key_elements": "关键元素描述",
      "seedance_prompt": "English prompt optimized for Seedance 2.0..."
    }
  ]
}

注意：
- 分镜数量根据视频时长和内容复杂度自动决定（通常5-9个）
- 每个分镜的Seedance prompt要包含运镜指令、主体描述、环境氛围、视觉风格
- 爆款分析要用中文，分析要具体、有洞察力
"""


# Mapping of Chinese camera movements to English keywords
CAMERA_MOVEMENT_MAP = {
    "推": "push-in",
    "拉": "pull-out",
    "摇": "pan",
    "移": "tracking",
    "跟": "following",
    "升": "crane-up",
    "降": "crane-down",
    "固定": "static",
    "环绕": "orbit",
}

# Default style keywords appended to every Seedance prompt
DEFAULT_STYLE_KEYWORDS = (
    "cinematic lighting, product showcase, "
    "high-end commercial, 4K, shallow depth of field"
)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class VideoAnalyzer:
    """Analyze videos for viral potential and generate storyboards."""

    def __init__(self):
        settings = get_settings()
        self._temp_dir = Path(settings.temp_path)

    # ------------------------------------------------------------------
    # Step 1 - Extract keyframes via ffmpeg
    # ------------------------------------------------------------------

    async def _get_video_duration(self, video_path: str) -> float:
        """Use ffprobe to get video duration in seconds."""
        proc = await asyncio.create_subprocess_exec(
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffprobe failed (rc={proc.returncode}): {stderr.decode().strip()}"
            )
        return float(stdout.decode().strip())

    async def extract_keyframes(self, video_path: str, max_frames: int = 12) -> List[str]:
        """Extract evenly-spaced keyframes and return them as base64 JPEG strings.

        Args:
            video_path: Absolute path to the source video file.
            max_frames: Maximum number of frames to extract.

        Returns:
            A list of base64-encoded JPEG image strings.
        """
        video_path = str(Path(video_path).resolve())
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}")

        interval = duration / max_frames

        # Prepare a unique temp directory for this extraction
        job_id = uuid.uuid4().hex[:12]
        frame_dir = self._temp_dir / f"frames_{job_id}"
        frame_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Run ffmpeg to extract frames
            output_pattern = str(frame_dir / "frame_%03d.jpg")
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-vf", f"fps=1/{interval}",
                "-frames:v", str(max_frames),
                "-q:v", "2",
                output_pattern,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed (rc={proc.returncode}): {stderr.decode().strip()}"
                )

            # Read and base64-encode the extracted frames
            frames: List[str] = []
            for frame_file in sorted(frame_dir.glob("frame_*.jpg")):
                raw = frame_file.read_bytes()
                frames.append(base64.b64encode(raw).decode("ascii"))

            logger.info("Extracted %d keyframes from %s", len(frames), video_path)
            return frames

        finally:
            # Cleanup temp frames
            shutil.rmtree(frame_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Step 2 - Call Qwen VL for analysis
    # ------------------------------------------------------------------

    async def analyze_with_qwen(
        self,
        keyframes: List[str],
        user_intent: str,
        client: AsyncOpenAI,
        model: str,
    ) -> dict:
        """Send keyframes to Qwen VL and get viral analysis + storyboard.

        Args:
            keyframes: List of base64-encoded JPEG strings.
            user_intent: User's intent for the analysis.
            client: AsyncOpenAI client instance (from provider_router).
            model: Model name to use.

        Returns:
            Parsed dict with 'viral_analysis' and 'storyboard' keys.
        """
        # Build the multimodal message content
        content: list = [
            {
                "type": "text",
                "text": f"用户意图：{user_intent}\n\n请分析以下视频关键帧，完成两个任务：\n1. 从6个核心维度进行爆款视频分析\n2. 将视频拆解为分镜头",
            },
        ]
        for b64 in keyframes:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                }
            )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            temperature=0.7,
            max_tokens=8192,  # 更大的token限制，因为需要输出更多内容
        )

        raw_text = response.choices[0].message.content.strip()
        logger.debug("Video analysis raw response: %s", raw_text[:500])

        # Parse JSON from the response
        json_text = raw_text
        if "```" in json_text:
            # Extract JSON block from markdown code fences
            parts = json_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    json_text = part
                    break

        result = json.loads(json_text)
        if not isinstance(result, dict):
            raise ValueError("Qwen VL response is not a JSON object")

        # Validate required keys
        if "viral_analysis" not in result:
            result["viral_analysis"] = []
        if "storyboard" not in result:
            result["storyboard"] = []

        logger.info(
            "Video analysis returned %d viral dimensions and %d storyboard shots",
            len(result["viral_analysis"]),
            len(result["storyboard"]),
        )
        return result

    # ------------------------------------------------------------------
    # Step 3 - Generate Seedance-optimized prompts
    # ------------------------------------------------------------------

    @staticmethod
    def generate_seedance_prompt(shot_data: dict) -> str:
        """Convert a shot dict into a Seedance-optimized English prompt."""
        camera_cn = shot_data.get("camera_movement", "固定")
        camera_en = CAMERA_MOVEMENT_MAP.get(camera_cn, "static")

        # Prefer the seedance_prompt field if already provided
        description_en = shot_data.get("seedance_prompt", "")
        if not description_en:
            # Fall back to Chinese description
            description_en = shot_data.get("description_cn", "")

        key_elements = shot_data.get("key_elements", "")

        parts = [
            f"{camera_en} shot",
            description_en.strip().rstrip("."),
        ]
        if key_elements:
            parts.append(key_elements.strip().rstrip("."))
        parts.append(DEFAULT_STYLE_KEYWORDS)

        return ", ".join(p for p in parts if p)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def analyze(
        self,
        video_path: str,
        user_intent: str,
        client: AsyncOpenAI = None,
        model: str = None,
    ) -> VideoAnalysisResult:
        """Run the full video analysis pipeline.

        Args:
            video_path: Absolute path to the reference video.
            user_intent: User's intent for the analysis.
            client: AsyncOpenAI client (from provider_router). If None, will
                    resolve via provider_router using a new DB session.
            model: Model name. If None, will resolve from provider_router.

        Returns:
            A VideoAnalysisResult with viral analysis and storyboard.
        """
        # 如果未传入 client/model，通过 provider_router 解析
        if client is None or model is None:
            from ..db.database import SessionLocal
            db = SessionLocal()
            try:
                rp = resolve_provider(db, "analysis")
                client = rp.client
                model = rp.model
            finally:
                db.close()

        logger.info("Starting video analysis for %s", video_path)

        # Step 1 - Extract keyframes
        try:
            keyframes = await self.extract_keyframes(video_path)
        except Exception:
            logger.exception("Keyframe extraction failed")
            raise

        if not keyframes:
            raise RuntimeError("No keyframes were extracted from the video")

        # Step 2 - Call Qwen VL
        try:
            analysis_data = await self.analyze_with_qwen(keyframes, user_intent, client, model)
        except Exception:
            logger.exception("Qwen VL analysis failed")
            raise

        # Step 3 - Build result objects
        viral_analysis: List[ViralDimension] = []
        for vd in analysis_data.get("viral_analysis", []):
            viral_analysis.append(ViralDimension(
                dimension=vd.get("dimension", ""),
                analysis=vd.get("analysis", ""),
            ))

        storyboard: List[StoryboardShot] = []
        for sd in analysis_data.get("storyboard", []):
            seedance = self.generate_seedance_prompt(sd)
            shot = StoryboardShot(
                shot_id=sd.get("shot_id", 0),
                description_cn=sd.get("description_cn", ""),
                camera_movement=sd.get("camera_movement", "固定"),
                duration=sd.get("duration", 3),
                key_elements=sd.get("key_elements", ""),
                seedance_prompt=seedance,
            )
            storyboard.append(shot)

        analysis_id = f"video_analysis_{uuid.uuid4().hex[:12]}"

        result = VideoAnalysisResult(
            analysis_id=analysis_id,
            video_url=None,  # Will be set by the caller if needed
            intent=user_intent,
            viral_analysis=viral_analysis,
            storyboard=storyboard,
        )

        logger.info(
            "Video analysis complete: %d viral dimensions, %d storyboard shots",
            len(viral_analysis),
            len(storyboard),
        )
        return result


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_analyzer_instance: Optional[VideoAnalyzer] = None


def get_video_analyzer() -> VideoAnalyzer:
    """Get or create a singleton VideoAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = VideoAnalyzer()
    return _analyzer_instance
