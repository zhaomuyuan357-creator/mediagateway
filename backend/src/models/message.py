"""Message model."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..db.database import Base


class MessageRole(str, enum.Enum):
    """Message role enum."""

    USER = "user"
    ASSISTANT = "assistant"


class MessageType(str, enum.Enum):
    """Message type enum."""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    STORYBOARD = "storyboard"
    ANALYSIS = "analysis"
    CONFIRMATION = "confirmation"


class Message(Base):
    """Message model for chat messages."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(SQLEnum(MessageRole), nullable=False, index=True)
    content = Column(String, nullable=True)
    message_type = Column(SQLEnum(MessageType), default=MessageType.TEXT, nullable=False)
    extra_metadata = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role.value,
            "content": self.content,
            "message_type": self.message_type.value,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.isoformat(),
        }
