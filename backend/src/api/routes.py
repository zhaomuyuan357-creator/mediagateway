"""API routes — 重构后统一使用 Task + APIProvider."""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
import uuid
import json
import shutil
from datetime import datetime
from pathlib import Path

from ..db.database import get_db
from ..models import (
    APIProvider, Task, TaskType, TaskStatus,
    Conversation, ConversationType,
    Message, MessageRole, MessageType,
)
from ..services.encryption import get_encryption_service
from ..services.provider_router import reload_weights
from ..services.pipeline import execute_pipeline
from .schemas import (
    APIProviderCreate, APIProviderUpdate, APIProviderResponse,
    TaskCreate, TaskResponse, TaskListResponse,
    ConversationCreate, ConversationResponse, ConversationDetailResponse, ConversationUpdate,
    MessageCreate, MessageResponse,
    MaterialResponse, MaterialListResponse,
)

router = APIRouter()


# ============ 中转站管理（APIProvider CRUD） ============

@router.post("/v1/providers", response_model=APIProviderResponse)
def create_provider(request: APIProviderCreate, db: Session = Depends(get_db)):
    """创建中转站."""
    encryption = get_encryption_service()
    encrypted_key = encryption.encrypt(request.api_key)

    provider = APIProvider(
        name=request.name,
        base_url=request.base_url.rstrip("/"),
        encrypted_key=encrypted_key,
        model_mapping=request.model_mapping,
        weight=request.weight,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)

    # 清除路由缓存，下次请求时重新加载
    reload_weights()

    return APIProviderResponse(
        id=provider.id,
        name=provider.name,
        base_url=provider.base_url,
        model_mapping=provider.model_mapping,
        weight=provider.weight,
        is_active=provider.is_active,
        key_preview=provider.to_dict(include_key=True).get("key_preview"),
        created_at=provider.created_at.isoformat() if provider.created_at else None,
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None,
    )


@router.get("/v1/providers", response_model=List[APIProviderResponse])
def list_providers(db: Session = Depends(get_db)):
    """列出所有中转站."""
    providers = db.query(APIProvider).order_by(APIProvider.id).all()
    return [
        APIProviderResponse(
            id=p.id,
            name=p.name,
            base_url=p.base_url,
            model_mapping=p.model_mapping,
            weight=p.weight,
            is_active=p.is_active,
            key_preview=p.to_dict(include_key=True).get("key_preview"),
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in providers
    ]


@router.get("/v1/providers/{provider_id}", response_model=APIProviderResponse)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """获取单个中转站."""
    provider = db.query(APIProvider).filter(APIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    return APIProviderResponse(
        id=provider.id,
        name=provider.name,
        base_url=provider.base_url,
        model_mapping=provider.model_mapping,
        weight=provider.weight,
        is_active=provider.is_active,
        key_preview=provider.to_dict(include_key=True).get("key_preview"),
        created_at=provider.created_at.isoformat() if provider.created_at else None,
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None,
    )


@router.patch("/v1/providers/{provider_id}", response_model=APIProviderResponse)
def update_provider(
    provider_id: int,
    request: APIProviderUpdate,
    db: Session = Depends(get_db),
):
    """更新中转站."""
    provider = db.query(APIProvider).filter(APIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if request.name is not None:
        provider.name = request.name
    if request.base_url is not None:
        provider.base_url = request.base_url.rstrip("/")
    if request.api_key is not None:
        encryption = get_encryption_service()
        provider.encrypted_key = encryption.encrypt(request.api_key)
    if request.model_mapping is not None:
        provider.model_mapping = request.model_mapping
    if request.weight is not None:
        provider.weight = request.weight
    if request.is_active is not None:
        provider.is_active = request.is_active

    db.commit()
    db.refresh(provider)
    reload_weights()

    return APIProviderResponse(
        id=provider.id,
        name=provider.name,
        base_url=provider.base_url,
        model_mapping=provider.model_mapping,
        weight=provider.weight,
        is_active=provider.is_active,
        key_preview=provider.to_dict(include_key=True).get("key_preview"),
        created_at=provider.created_at.isoformat() if provider.created_at else None,
        updated_at=provider.updated_at.isoformat() if provider.updated_at else None,
    )


@router.delete("/v1/providers/{provider_id}")
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """删除中转站."""
    provider = db.query(APIProvider).filter(APIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    db.delete(provider)
    db.commit()
    reload_weights()
    return {"message": "Provider deleted successfully"}


# ============ 任务管理（Task CRUD） ============

@router.post("/v1/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """创建任务 → 后台自动执行 pipeline."""
    # 校验 task_type
    try:
        task_type = TaskType(request.task_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 task_type: {request.task_type}，支持: image / video / analysis",
        )

    # 生成唯一 task_id
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    task = Task(
        task_id=task_id,
        task_type=task_type,
        status=TaskStatus.PENDING,
        payload=request.payload,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 后台执行流水线
    background_tasks.add_task(execute_pipeline, task_id)

    return _task_to_response(task)


@router.get("/v1/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """查询任务状态（前端轮询用）."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.get("/v1/tasks", response_model=TaskListResponse)
def list_tasks(
    page: int = 1,
    page_size: int = 20,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """列出任务（支持分页、按 type/status 筛选）."""
    query = db.query(Task)

    if task_type:
        query = query.filter(Task.task_type == task_type)
    if status:
        query = query.filter(Task.status == status)

    total = query.count()
    tasks = (
        query.order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TaskListResponse(
        items=[_task_to_response(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/v1/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}


# ============ 对话管理（保留） ============

@router.post("/v1/conversations", response_model=ConversationResponse)
def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation."""
    conv_type = ConversationType(request.type)
    title = request.title or ("新视频对话" if conv_type == ConversationType.VIDEO else "新图片对话")

    conversation = Conversation(
        type=conv_type,
        title=title,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        type=conversation.type.value,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=0,
    )


@router.get("/v1/conversations", response_model=List[ConversationResponse])
def list_conversations(
    skip: int = 0,
    limit: int = 50,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all conversations."""
    query = db.query(Conversation)
    if type:
        query = query.filter(Conversation.type == type)
    conversations = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

    return [
        ConversationResponse(
            id=conv.id,
            type=conv.type.value,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat(),
            message_count=len(conv.messages) if hasattr(conv, "messages") else 0,
        )
        for conv in conversations
    ]


@router.get("/v1/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Get conversation detail with messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role.value,
            content=msg.content,
            message_type=msg.message_type.value,
            metadata=msg.extra_metadata,
            created_at=msg.created_at.isoformat(),
        )
        for msg in conversation.messages
    ]

    return ConversationDetailResponse(
        id=conversation.id,
        type=conversation.type.value,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=len(messages),
        messages=messages,
    )


@router.patch("/v1/conversations/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    request: ConversationUpdate,
    db: Session = Depends(get_db),
):
    """Update conversation (e.g., title)."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.title is not None:
        conversation.title = request.title

    db.commit()
    db.refresh(conversation)

    return ConversationResponse(
        id=conversation.id,
        type=conversation.type.value,
        title=conversation.title,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat(),
        message_count=len(conversation.messages) if hasattr(conversation, "messages") else 0,
    )


@router.delete("/v1/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully"}


# ============ 消息管理（保留） ============

@router.post("/v1/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def create_message(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    content: Optional[str] = Form(None),
    message_type: str = Form("text"),
    metadata: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    """Send a message in a conversation.

    Supports:
    - Text messages
    - Image/video uploads (files are saved and URLs stored in metadata)
    """
    # Verify conversation exists
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Parse metadata
    meta = json.loads(metadata) if metadata else {}

    # Handle file uploads (support multiple files)
    if files and len(files) > 0:
        from ..config import get_settings
        settings = get_settings()

        image_urls = []
        video_urls = []
        msg_type = MessageType.TEXT

        for file in files:
            # Determine file type and save location
            file_ext = Path(file.filename).suffix if file.filename else ".bin"
            is_image = file_ext.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}
            is_video = file_ext.lower() in {".mp4", ".mov", ".avi", ".webm"}

            if is_image:
                save_dir = Path(settings.storage_path) / "images"
                msg_type = MessageType.IMAGE
            elif is_video:
                save_dir = Path(settings.storage_path) / "videos"
                msg_type = MessageType.VIDEO
            else:
                save_dir = Path(settings.temp_path)

            save_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{uuid.uuid4().hex[:12]}{file_ext}"
            file_path = save_dir / filename

            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Store relative URL
            if is_image:
                image_urls.append(f"/images/{filename}")
            elif is_video:
                video_urls.append(f"/videos/{filename}")

        # Store in metadata — support both single and multiple
        if image_urls:
            meta["image_url"] = image_urls[0]  # primary
            if len(image_urls) > 1:
                meta["image_urls"] = image_urls
        if video_urls:
            meta["video_url"] = video_urls[0]
            if len(video_urls) > 1:
                meta["video_urls"] = video_urls
        meta["original_filenames"] = [f.filename for f in files]
    else:
        msg_type = MessageType(message_type)

    # Create message
    message = Message(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=content,
        message_type=msg_type,
        extra_metadata=meta,
    )
    db.add(message)

    # Update conversation timestamp and auto-generate title from first message
    conversation.updated_at = datetime.utcnow()
    if conversation.title == "新对话" and content:
        conversation.title = content[:50] + ("..." if len(content) > 50 else "")

    db.commit()
    db.refresh(message)

    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role.value,
        content=message.content,
        message_type=message.message_type.value,
        metadata=message.extra_metadata,
        created_at=message.created_at.isoformat(),
    )


@router.get("/v1/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
def list_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List messages in a conversation."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role.value,
            content=msg.content,
            message_type=msg.message_type.value,
            metadata=msg.extra_metadata,
            created_at=msg.created_at.isoformat(),
        )
        for msg in messages
    ]


# ============ 素材库（改为从 Task 表读取） ============

@router.get("/v1/materials", response_model=MaterialListResponse)
def list_materials(
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    conversation_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """List all materials (completed image/video tasks) with filtering."""
    from datetime import datetime as dt
    from sqlalchemy import func, and_, cast, String

    query = db.query(Task).filter(
        Task.status == TaskStatus.SUCCESS,
        Task.task_type.in_([TaskType.IMAGE, TaskType.VIDEO]),
    )

    filters = []

    if type:
        filters.append(Task.task_type == type)

    if date_from:
        try:
            filters.append(Task.created_at >= dt.fromisoformat(date_from))
        except Exception:
            pass

    if date_to:
        try:
            filters.append(Task.created_at <= dt.fromisoformat(date_to))
        except Exception:
            pass

    if conversation_id:
        filters.append(
            cast(Task.payload, String).like(f'%"conversation_id": {conversation_id}%')
        )

    if keyword:
        filters.append(cast(Task.payload, String).ilike(f"%{keyword}%"))

    if filters:
        query = query.filter(and_(*filters))

    total = query.count()

    tasks = (
        query.order_by(Task.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Collect conversation IDs for batch lookup
    conv_ids = set()
    for t in tasks:
        cid = (t.payload or {}).get("conversation_id")
        if cid:
            conv_ids.add(cid)

    conv_titles: Dict[int, str] = {}
    if conv_ids:
        conversations = db.query(Conversation).filter(Conversation.id.in_(conv_ids)).all()
        conv_titles = {c.id: c.title for c in conversations}

    items = []
    for t in tasks:
        items.append(_task_to_material(t, conv_titles))

    return MaterialListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        conversations=conv_titles if conv_titles else None,
    )


@router.get("/v1/materials/{task_id}")
def get_material(task_id: str, db: Session = Depends(get_db)):
    """Get a single material detail."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Material not found")

    conv_titles: Dict[int, str] = {}
    cid = (task.payload or {}).get("conversation_id")
    if cid:
        conv = db.query(Conversation).filter(Conversation.id == cid).first()
        if conv:
            conv_titles[cid] = conv.title

    return _task_to_material(task, conv_titles)


@router.delete("/v1/materials/{task_id}")
def delete_material(task_id: str, db: Session = Depends(get_db)):
    """Delete a material."""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Material not found")

    # Delete associated file if exists
    if task.result_url:
        try:
            result_data = json.loads(task.result_url)
            from ..services.video_storage import get_video_storage
            storage = get_video_storage()
            video_path = result_data.get("video_url", "")
            if video_path and video_path.startswith("/videos/"):
                filename = video_path.split("/")[-1]
                storage.delete_video(filename)
        except Exception:
            pass

    db.delete(task)
    db.commit()
    return {"message": "Material deleted successfully"}


# ============ 内部辅助函数 ============

def _task_to_response(task: Task) -> TaskResponse:
    """将 Task ORM 对象转为 TaskResponse schema."""
    return TaskResponse(
        id=task.id,
        task_id=task.task_id,
        task_type=task.task_type.value if task.task_type else "",
        status=task.status.value if task.status else "",
        provider_id=task.provider_id,
        provider_name=task.provider_name,
        payload=task.payload or {},
        result_url=task.result_url,
        error_msg=task.error_msg,
        progress=task.progress,
        created_at=task.created_at.isoformat() if task.created_at else None,
        updated_at=task.updated_at.isoformat() if task.updated_at else None,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


def _task_to_material(task: Task, conv_titles: Dict[int, str]) -> MaterialResponse:
    """将 Task ORM 对象转为 MaterialResponse schema."""
    payload = task.payload or {}
    result_data = {}
    if task.result_url:
        try:
            result_data = json.loads(task.result_url)
        except (json.JSONDecodeError, TypeError):
            pass

    # 提取 URL
    all_urls = []
    if task.task_type == TaskType.IMAGE:
        all_urls = result_data.get("image_urls", [])
    elif task.task_type == TaskType.VIDEO:
        video_url = result_data.get("video_url", "")
        if video_url:
            all_urls = [video_url]

    url = all_urls[0] if all_urls else ""
    conv_id = payload.get("conversation_id")

    # 计算生成耗时
    generation_time = None
    if task.started_at and task.completed_at:
        generation_time = (task.completed_at - task.started_at).total_seconds()

    return MaterialResponse(
        id=task.task_id,
        type=task.task_type.value if task.task_type else "",
        url=url,
        urls=all_urls if len(all_urls) > 1 else None,
        prompt=payload.get("prompt"),
        provider=task.provider_name,
        model=result_data.get("model"),
        conversation_id=conv_id,
        conversation_title=conv_titles.get(conv_id) if conv_id else None,
        created_at=task.created_at.isoformat() if task.created_at else "",
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration=payload.get("duration"),
        width=None,
        height=None,
        cost=None,
        generation_time=generation_time,
        metadata=payload,
    )
