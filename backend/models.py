"""
backend/models.py
-----------------
SQLAlchemy ORM models:
  - User          → accounts (email/password or Google OAuth)
  - Conversation  → a named chat session belonging to a user
  - Message       → individual turns (user | assistant) inside a conversation
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    name          = Column(String(255), nullable=True)
    # hashed password — NULL for Google-OAuth-only accounts
    hashed_password = Column(String(255), nullable=True)
    # OAuth provider info
    provider      = Column(String(50), nullable=True)  # "google" | None
    provider_id   = Column(String(255), nullable=True)

    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user",
                                 cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id         = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id    = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    title      = Column(String(500), nullable=False, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user     = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation",
                            cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    conversation_id = Column(UUID(as_uuid=False),
                             ForeignKey("conversations.id"), nullable=False)
    role            = Column(SAEnum("user", "assistant", name="message_role"),
                             nullable=False)
    content         = Column(Text, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")
