"""API Provider model — 动态中转站管理."""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from datetime import datetime
from ..db.database import Base


class APIProvider(Base):
    """动态中转站配置表。

    每条记录对应一个物理中转站（base_url + api_key）。
    通过 model_mapping 声明该中转站支持的 task_type 及对应模型名，
    格式: {"image": "dall-e-3", "video": "seedance-2.0-t2v", "analysis": "gpt-4o"}
    """

    __tablename__ = "api_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, comment="中转站显示名称")
    base_url = Column(String, nullable=False, comment="API 基础地址")
    encrypted_key = Column(String, nullable=False, comment="加密后的 API Key")

    model_mapping = Column(
        JSON,
        nullable=False,
        default=dict,
        comment='任务类型→模型名映射，如 {"image": "dall-e-3", "video": "seedance-2.0-t2v"}',
    )

    weight = Column(Integer, default=1, nullable=False, comment="权重，用于加权轮询选择")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # ---- 序列化 ----

    def to_dict(self, include_key: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "base_url": self.base_url,
            "model_mapping": self.model_mapping or {},
            "weight": self.weight,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_key:
            data["key_preview"] = (
                f"{self.encrypted_key[:8]}...{self.encrypted_key[-4:]}"
                if self.encrypted_key and len(self.encrypted_key) > 12
                else "****"
            )
        return data
