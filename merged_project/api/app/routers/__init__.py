"""Routers module.

Contains FastAPI routers for ChronicAI API:
- upload: File upload and document ingestion
- chat: AI-powered medical chat
- doctor: Doctor-specific endpoints
"""
from app.routers.upload import router as upload_router
from app.routers.chat import router as chat_router
from app.routers.doctor import router as doctor_router

__all__ = ["upload_router", "chat_router", "doctor_router"]
