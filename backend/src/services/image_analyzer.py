"""Image analysis service - analyze product images and generate prompts for different use cases."""
import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from openai import AsyncOpenAI

from ..config import get_settings
from ..services.provider_router import resolve_provider

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class PromptSuggestion:
    """A single prompt suggestion for image generation."""

    id: str
    purpose: str  # e.g., "电商主图", "产品详情页", "社交媒体图"
    prompt: str  # English prompt
    prompt_cn: Optional[str] = None  # Chinese translation for reference
    selected: bool = True  # Whether this prompt is selected by default

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ImageAnalysisResult:
    """Result of image analysis."""

    analysis_id: str
    image_url: str
    intent: str
    prompts: List[PromptSuggestion] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "image_url": self.image_url,
            "intent": self.intent,
            "prompts": [p.to_dict() for p in self.prompts],
        }


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个专业的电商视觉营销专家和AI图像生成提示词工程师。

用户会上传一张产品图片，并说明他们的营销意图（如"生成美国独立日主题"、"制作圣诞节促销图"等）。

你的任务是：
1. 分析产品图片中的产品特征（产品类型、颜色、材质、形状等）
2. 根据用户的营销意图，生成多条不同用途的英文提示词

每条提示词需要：
- 保持产品外观不变，只改变背景/场景/氛围
- 适合OpenAI gpt-image-1模型生成
- 包含详细的场景描述、光线、色调、构图建议
- 用英文撰写，因为AI图像生成模型对英文响应更好

请输出JSON数组格式，包含3-5条不同用途的提示词：
[
  {
    "id": "1",
    "purpose": "用途名称（中文）",
    "purpose_en": "Purpose name in English",
    "prompt": "Detailed English prompt for image generation...",
    "prompt_cn": "中文翻译供参考"
  }
]

用途建议（可根据用户意图调整）：
- 电商主图：简洁、专业、突出产品
- 产品详情页：展示产品细节、使用场景
- 社交媒体图：吸引眼球、适合分享
- 广告Banner：大尺寸、有冲击力
- 节日/活动主题图：根据用户指定的节日/活动
"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ImageAnalyzer:
    """Analyze product images and generate prompts for different use cases."""

    def __init__(self):
        pass  # 不再持有客户端状态，每次调用时通过 provider_router 获取

    async def analyze(
        self,
        image_url: str,
        user_intent: str,
        client: AsyncOpenAI = None,
        model: str = None,
    ) -> ImageAnalysisResult:
        """Analyze an image and generate prompt suggestions.

        Args:
            image_url: URL or base64 data URI of the product image.
            user_intent: User's marketing intent (e.g., "生成美国独立日主题").
            client: AsyncOpenAI client (from provider_router). If None, will
                    resolve via provider_router using a new DB session.
            model: Model name. If None, will resolve from provider_router.

        Returns:
            An ImageAnalysisResult containing multiple prompt suggestions.
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

        logger.info("Starting image analysis for intent: %s", user_intent[:50])

        # Build the multimodal message content
        content: list = [
            {"type": "text", "text": f"用户意图：{user_intent}\n\n请分析这张产品图片，并根据用户意图生成3-5条不同用途的英文提示词。"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]

        try:
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
            logger.debug("Image analysis raw response: %s", raw_text[:500])

            # Parse JSON from response
            prompts_data = self._parse_json_response(raw_text)

            # Build prompt suggestions
            prompts: List[PromptSuggestion] = []
            for idx, pd in enumerate(prompts_data):
                prompt = PromptSuggestion(
                    id=pd.get("id", str(idx + 1)),
                    purpose=pd.get("purpose", f"用途{idx + 1}"),
                    prompt=pd.get("prompt", ""),
                    prompt_cn=pd.get("prompt_cn"),
                    selected=True,
                )
                prompts.append(prompt)

            analysis_id = f"img_analysis_{uuid.uuid4().hex[:12]}"

            result = ImageAnalysisResult(
                analysis_id=analysis_id,
                image_url=image_url,
                intent=user_intent,
                prompts=prompts,
            )

            logger.info("Image analysis complete: %d prompts generated", len(prompts))
            return result

        except Exception as e:
            logger.exception("Image analysis failed")
            raise RuntimeError(f"Image analysis failed: {str(e)}")

    @staticmethod
    def _parse_json_response(text: str) -> list:
        """Parse JSON array from response text, handling markdown fences."""
        json_text = text
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

        result = json.loads(json_text)
        if not isinstance(result, list):
            raise ValueError("Response is not a JSON array")
        return result


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

_analyzer_instance: Optional[ImageAnalyzer] = None


def get_image_analyzer() -> ImageAnalyzer:
    """Get or create a singleton ImageAnalyzer instance."""
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ImageAnalyzer()
    return _analyzer_instance
