"""Conversation model."""
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..db.database import Base


class ConversationType(str, enum.Enum):
    """Conversation type enum."""

    VIDEO = "video"
    IMAGE = "image"


class Conversation(Base):
    """Conversation model for chat sessions."""

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(SQLEnum(ConversationType), nullable=False, index=True)
    title = Column(String, nullable=False, default="新对话")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    def to_dict(self, include_messages: bool = False):
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_messages and hasattr(self, "messages"):
            data["messages"] = [msg.to_dict() for msg in self.messages]
        return data
