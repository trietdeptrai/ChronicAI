"""
Chat History Service - Persistence layer for chat conversations and messages.

Provides CRUD operations for storing and retrieving chat history
for both doctor and patient chat interfaces.
"""

import logging
from typing import Optional
from uuid import UUID

from app.db.database import get_supabase

logger = logging.getLogger(__name__)


def create_conversation(
    conversation_type: str,
    user_id: str,
    title: Optional[str] = None,
) -> dict:
    """
    Create a new chat conversation.

    Args:
        conversation_type: 'doctor' or 'patient'
        user_id: The doctor or patient UUID
        title: Optional conversation title (auto-generated later if None)

    Returns:
        The created conversation record
    """
    supabase = get_supabase()

    data = {
        "conversation_type": conversation_type,
        "user_id": str(user_id),
    }
    if title:
        data["title"] = title[:500]  # enforce max length

    result = supabase.table("chat_conversations").insert(data).execute()

    if not result.data:
        raise RuntimeError("Failed to create conversation")

    logger.info(
        "Created %s conversation %s for user %s",
        conversation_type,
        result.data[0]["id"],
        user_id,
    )
    return result.data[0]


def save_message(
    conversation_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Save a message to a conversation.

    Also updates the conversation's updated_at timestamp and
    auto-generates a title from the first user message if missing.

    Args:
        conversation_id: UUID of the conversation
        role: 'user' or 'assistant'
        content: Message text
        metadata: Optional dict with attachments, mentioned_patients, etc.

    Returns:
        The created message record
    """
    supabase = get_supabase()

    # Insert the message
    msg_data = {
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
        "metadata": metadata or {},
    }

    result = supabase.table("chat_messages").insert(msg_data).execute()

    if not result.data:
        raise RuntimeError("Failed to save message")

    # Touch updated_at on the conversation
    supabase.table("chat_conversations").update(
        {"updated_at": "now()"}
    ).eq("id", str(conversation_id)).execute()

    # Auto-generate title from first user message if conversation has no title
    if role == "user":
        conv = (
            supabase.table("chat_conversations")
            .select("title")
            .eq("id", str(conversation_id))
            .single()
            .execute()
        )
        if conv.data and not conv.data.get("title"):
            auto_title = content[:100].strip()
            if len(content) > 100:
                auto_title += "..."
            supabase.table("chat_conversations").update(
                {"title": auto_title}
            ).eq("id", str(conversation_id)).execute()

    return result.data[0]


def get_conversations(
    conversation_type: str,
    user_id: str,
    limit: int = 50,
) -> list[dict]:
    """
    List conversations for a user, newest first.

    Args:
        conversation_type: 'doctor' or 'patient'
        user_id: The doctor or patient UUID
        limit: Maximum conversations to return

    Returns:
        List of conversation records
    """
    supabase = get_supabase()

    result = (
        supabase.table("chat_conversations")
        .select("id, conversation_type, user_id, title, created_at, updated_at")
        .eq("conversation_type", conversation_type)
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )

    return result.data or []


def get_messages(
    conversation_id: str,
    limit: int = 100,
) -> list[dict]:
    """
    Get messages for a conversation, oldest first.

    Args:
        conversation_id: UUID of the conversation
        limit: Maximum messages to return

    Returns:
        List of message records
    """
    supabase = get_supabase()

    result = (
        supabase.table("chat_messages")
        .select("id, conversation_id, role, content, metadata, created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )

    return result.data or []


def delete_conversation(conversation_id: str) -> bool:
    """
    Delete a conversation and all its messages (cascade).

    Args:
        conversation_id: UUID of the conversation

    Returns:
        True if deleted successfully
    """
    supabase = get_supabase()

    result = (
        supabase.table("chat_conversations")
        .delete()
        .eq("id", str(conversation_id))
        .execute()
    )

    deleted = bool(result.data)
    if deleted:
        logger.info("Deleted conversation %s", conversation_id)
    return deleted


def update_conversation_title(conversation_id: str, title: str) -> dict:
    """
    Rename a conversation.

    Args:
        conversation_id: UUID of the conversation
        title: New title

    Returns:
        The updated conversation record
    """
    supabase = get_supabase()

    result = (
        supabase.table("chat_conversations")
        .update({"title": title[:500]})
        .eq("id", str(conversation_id))
        .execute()
    )

    if not result.data:
        raise RuntimeError("Failed to update conversation title")

    return result.data[0]
