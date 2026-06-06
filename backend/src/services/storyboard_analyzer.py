"""Storyboard analysis service - extract keyframes and generate structured shot data."""
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
class Shot:
    """A single storyboard shot."""

    shot_id: int
    description_cn: str
    camera_movement: str
    duration: int
    key_elements: str
    seedance_prompt: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Storyboard:
    """Complete storyboard consisting of multiple shots."""

    video_path: str
    video_duration: float
    shots: List[Shot] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "video_duration": self.video_duration,
            "shots": [s.to_dict() for s in self.shots],
        }


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的电商视频分镜师。请分析这些视频关键帧，将视频拆解为9个分镜头。

对每个分镜，请输出：
1. 画面描述（中文，详细描述画面内容和动作）
2. 运镜方式（推/拉/摇/移/跟/升/降/固定/环绕）
3. 时长建议（2-5秒）
4. 关键元素（主体产品、背景环境、光线、色调）
5. Seedance英文prompt（适合AI视频生成引擎的英文描述，包含运镜指令、主体描述、环境氛围、视觉风格）

请严格输出JSON数组格式，不要包含其他文字：
[
  {
    "shot_id": 1,
    "description_cn": "画面中文描述",
    "camera_movement": "运镜方式",
    "duration": 3,
    "key_elements": "关键元素描述",
    "seedance_prompt": "English prompt optimized for Seedance 2.0..."
  }
]"""

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

class StoryboardAnalyzer:
    """Analyze a reference video and produce a 9-shot storyboard."""

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

    async def extract_keyframes(self, video_path: str) -> List[str]:
        """Extract 12 evenly-spaced keyframes and return them as base64 JPEG strings.

        Args:
            video_path: Absolute path to the source video file.

        Returns:
            A list of base64-encoded JPEG image strings (length <= 12).
        """
        video_path = str(Path(video_path).resolve())
        duration = await self._get_video_duration(video_path)
        if duration <= 0:
            raise ValueError(f"Invalid video duration: {duration}")

        interval = duration / 12

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
                "-frames:v", "12",
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
        client: AsyncOpenAI,
        model: str,
    ) -> List[dict]:
        """Send keyframes to Qwen VL and get structured shot data.

        Args:
            keyframes: List of base64-encoded JPEG strings.
            client: AsyncOpenAI client instance (from provider_router).
            model: Model name to use.

        Returns:
            Parsed list of shot dictionaries (9 entries expected).
        """
        # Build the multimodal message content
        content: list = [
            {"type": "text", "text": "请分析以下视频关键帧，拆解为9个分镜头。"},
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
            max_tokens=4096,
        )

        raw_text = response.choices[0].message.content.strip()
        logger.debug("Qwen VL raw response: %s", raw_text[:500])

        # Try to parse JSON from the response (handle possible markdown fences)
        json_text = raw_text
        if "```" in json_text:
            # Extract JSON block from markdown code fences
            parts = json_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("["):
                    json_text = part
                    break

        shots_data = json.loads(json_text)
        if not isinstance(shots_data, list):
            raise ValueError("Qwen VL response is not a JSON array")

        logger.info("Qwen VL returned %d shots", len(shots_data))
        return shots_data

    # ------------------------------------------------------------------
    # Step 3 - Generate Seedance-optimized prompts
    # ------------------------------------------------------------------

    @staticmethod
    def generate_seedance_prompt(shot_data: dict) -> str:
        """Convert a Qwen VL shot dict into a Seedance-optimized English prompt.

        Format: ``{camera_movement} shot, {description_en}, {style_keywords}``

        This uses template-based translation and does NOT call an LLM.
        """
        camera_cn = shot_data.get("camera_movement", "固定")
        camera_en = CAMERA_MOVEMENT_MAP.get(camera_cn, "static")

        # Prefer the seedance_prompt field if Qwen already provided one
        description_en = shot_data.get("seedance_prompt", "")
        if not description_en:
            # Fall back to Chinese description (still usable)
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
        client: AsyncOpenAI = None,
        model: str = None,
    ) -> Storyboard:
        """Run the full storyboard analysis pipeline.

        Args:
            video_path: Absolute path to the reference video.
            client: AsyncOpenAI client (from provider_router). If None, will
                    resolve via provider_router using a new DB session.
            model: Model name. If None, will resolve from provider_router.

        Returns:
            A :class:`Storyboard` containing 9 :class:`Shot` instances.
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

        logger.info("Starting storyboard analysis for %s", video_path)

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
            shots_data = await self.analyze_with_qwen(keyframes, client, model)
        except Exception:
            logger.exception("Qwen VL analysis failed")
            raise

        # Step 3 - Build Shot objects with Seedance prompts
        shots: List[Shot] = []
        for sd in shots_data:
            seedance = self.generate_seedance_prompt(sd)
            shot = Shot(
                shot_id=sd.get("shot_id", 0),
                description_cn=sd.get("description_cn", ""),
                camera_movement=sd.get("camera_movement", "固定"),
                duration=sd.get("duration", 3),
                key_elements=sd.get("key_elements", ""),
                seedance_prompt=seedance,
            )
            shots.append(shot)

        # Get video duration for the storyboard metadata
        try:
            duration = await self._get_video_duration(video_path)
        except Exception:
            duration = 0.0

        storyboard = Storyboard(
            video_path=str(Path(video_path).resolve()),
            video_duration=duration,
            shots=shots,
        )

        logger.info(
            "Storyboard analysis complete: %d shots generated", len(shots)
        )
        return storyboard


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_analyzer_instance: Optional[StoryboardAnalyzer] = None


def get_storyboard_analyzer() -> StoryboardAnalyzer:
    """Get or create a singleton StoryboardAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = StoryboardAnalyzer()
    return _analyzer_instance
