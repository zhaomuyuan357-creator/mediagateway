"""Task model — 统一异步任务追踪."""
import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum as SQLEnum, Text
from ..db.database import Base


class TaskType(str, enum.Enum):
    """任务类型."""

    IMAGE = "image"
    VIDEO = "video"
    ANALYSIS = "analysis"


class TaskStatus(str, enum.Enum):
    """任务状态."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class Task(Base):
    """统一任务表。

    所有异步操作（图片生成、视频生成、视觉分析）统一走这张表。
    payload 字段存储完整的请求参数，由 execute_pipeline 解析后执行。
    """

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, nullable=False, index=True, comment="对外暴露的任务 ID，如 task_a1b2c3")
    task_type = Column(SQLEnum(TaskType), nullable=False, index=True, comment="image / video / analysis")
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False, index=True)

    provider_id = Column(Integer, nullable=True, index=True, comment="实际执行的 APIProvider ID")
    provider_name = Column(String, nullable=True, comment="中转站名称（冗余，方便查询）")

    payload = Column(JSON, nullable=False, default=dict, comment="完整的请求参数")
    result_url = Column(String, nullable=True, comment="生成结果 URL（图片/视频/分析 JSON）")
    error_msg = Column(Text, nullable=True, comment="失败时的错误信息")

    progress = Column(String, nullable=True, comment="当前流水线阶段描述，如 'analyzing' / 'generating'")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True, comment="开始执行时间")
    completed_at = Column(DateTime, nullable=True, comment="完成/失败时间")

    # ---- 序列化 ----

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "task_type": self.task_type.value if self.task_type else None,
            "status": self.status.value if self.status else None,
            "provider_id": self.provider_id,
            "provider_name": self.provider_name,
            "payload": self.payload,
            "result_url": self.result_url,
            "error_msg": self.error_msg,
            "progress": self.progress,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
