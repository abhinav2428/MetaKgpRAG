"""
backend/routers/conversations_router.py
---------------------------------------
Routes:
  GET    /conversations           → list all conversations for current user
  POST   /conversations           → create a new conversation
  GET    /conversations/{id}      → get a conversation with all its messages
  DELETE /conversations/{id}      → delete a conversation
  PATCH  /conversations/{id}      → rename a conversation
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user_required

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _get_conversation_or_404(
    conv_id: str, user_id: str, db: Session
) -> models.Conversation:
    conv = (
        db.query(models.Conversation)
        .filter(
            models.Conversation.id == conv_id,
            models.Conversation.user_id == user_id,
        )
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conv


@router.get("", response_model=list[schemas.ConversationOut])
def list_conversations(
    payload: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    user_id = payload["sub"]
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.updated_at.desc())
        .all()
    )


@router.post("", response_model=schemas.ConversationOut,
             status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: schemas.ConversationCreate,
    payload: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    user_id = payload["sub"]
    conv = models.Conversation(user_id=user_id, title=body.title or "New Conversation")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conv_id}", response_model=schemas.ConversationDetail)
def get_conversation(
    conv_id: str,
    payload: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    return _get_conversation_or_404(conv_id, payload["sub"], db)


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conv_id: str,
    payload: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    conv = _get_conversation_or_404(conv_id, payload["sub"], db)
    db.delete(conv)
    db.commit()


@router.patch("/{conv_id}", response_model=schemas.ConversationOut)
def rename_conversation(
    conv_id: str,
    body: schemas.ConversationCreate,
    payload: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    conv = _get_conversation_or_404(conv_id, payload["sub"], db)
    if body.title:
        conv.title = body.title
    db.commit()
    db.refresh(conv)
    return conv
