"""API request/response schemas — 重构后统一使用 Task + APIProvider."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


# ============ APIProvider（中转站管理） ============

class APIProviderCreate(BaseModel):
    """创建中转站请求."""

    name: str = Field(..., description="中转站显示名称")
    base_url: str = Field(..., description="API 基础地址，如 https://api.example.com/v1")
    api_key: str = Field(..., description="API Key（明文，后端加密存储）")
    model_mapping: Dict[str, str] = Field(
        ...,
        description='任务类型→模型名映射，如 {"image": "dall-e-3", "video": "seedance-2.0-t2v"}',
    )
    weight: int = Field(1, ge=1, description="权重，用于加权轮询")


class APIProviderUpdate(BaseModel):
    """更新中转站请求（所有字段可选）."""

    name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = Field(None, description="新 API Key（留空则不更新）")
    model_mapping: Optional[Dict[str, str]] = None
    weight: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class APIProviderResponse(BaseModel):
    """中转站响应."""

    id: int
    name: str
    base_url: str
    model_mapping: Dict[str, str]
    weight: int
    is_active: bool
    key_preview: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ============ Task（统一任务） ============

class TaskCreate(BaseModel):
    """创建任务请求 — 通用入口."""

    task_type: str = Field(..., description="任务类型: image / video / analysis")
    payload: Dict[str, Any] = Field(
        ...,
        description="任务参数。image/video: {prompt, ...}；analysis: {image_url, user_intent, ...}",
    )


class TaskResponse(BaseModel):
    """任务响应."""

    id: int
    task_id: str
    task_type: str
    status: str
    provider_id: Optional[int] = None
    provider_name: Optional[str] = None
    payload: Dict[str, Any]
    result_url: Optional[str] = None
    error_msg: Optional[str] = None
    progress: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class TaskListResponse(BaseModel):
    """任务列表响应（分页）."""

    items: List[TaskResponse]
    total: int
    page: int
    page_size: int


# ============ 对话管理（保留，与 Task 解耦） ============

class ConversationCreate(BaseModel):
    """创建对话请求."""

    type: str = Field(..., description="对话类型: video / image")
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    """对话响应."""

    id: int
    type: str
    title: str
    created_at: str
    updated_at: str
    message_count: Optional[int] = 0


class ConversationDetailResponse(ConversationResponse):
    """对话详情（含消息）."""

    messages: List["MessageResponse"] = []


class ConversationUpdate(BaseModel):
    """更新对话请求."""

    title: Optional[str] = None


# ============ 消息管理（保留） ============

class MessageCreate(BaseModel):
    """创建消息请求."""

    content: Optional[str] = None
    message_type: str = Field("text", description="消息类型: text / image / video / storyboard / analysis")
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(BaseModel):
    """消息响应."""

    id: int
    conversation_id: int
    role: str
    content: Optional[str] = None
    message_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


# ============ AI 分析（保留，供 analysis 任务使用） ============

class ImageAnalysisRequest(BaseModel):
    """图片分析请求."""

    user_intent: str = Field(..., description="用户意图，如 '生成美国独立日主题'")
    reference_image_url: Optional[str] = None


class PromptSuggestion(BaseModel):
    """单条 prompt 建议."""

    id: str
    purpose: str
    prompt: str
    prompt_cn: Optional[str] = None
    selected: bool = True


class ImageAnalysisResponse(BaseModel):
    """图片分析响应."""

    analysis_id: str
    image_url: str
    intent: str
    prompts: List[PromptSuggestion]
    status: str = "completed"


class VideoAnalysisRequest(BaseModel):
    """视频分析请求."""

    user_intent: str = Field(..., description="用户意图")
    video_url: Optional[str] = None


class ViralDimension(BaseModel):
    """爆款分析维度."""

    dimension: str
    analysis: str


class StoryboardShot(BaseModel):
    """分镜 shot."""

    shot_id: int
    description_cn: str
    camera_movement: str
    duration: int = 3
    key_elements: str
    seedance_prompt: str
    keyframe_url: Optional[str] = None


class VideoAnalysisResponse(BaseModel):
    """视频分析响应."""

    analysis_id: str
    video_url: Optional[str] = None
    intent: str
    viral_analysis: List[ViralDimension]
    storyboard: List[StoryboardShot]
    status: str = "completed"


# ============ 素材库（保留） ============

class MaterialResponse(BaseModel):
    """素材响应."""

    id: str
    type: str
    url: str
    urls: Optional[List[str]] = None
    prompt: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    conversation_id: Optional[int] = None
    conversation_title: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    cost: Optional[float] = None
    generation_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class MaterialListResponse(BaseModel):
    """素材列表响应."""

    items: List[MaterialResponse]
    total: int
    page: int
    page_size: int
    conversations: Optional[Dict[int, str]] = None


# Update forward references
ConversationDetailResponse.model_rebuild()
