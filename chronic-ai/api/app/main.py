import logging

# Configure logging to see translation debug messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import upload_router, chat_router, doctor_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("=" * 50)
    logger.info("SERVER STARTING")
    logger.info("=" * 50)

    yield  # Server runs here

    # Shutdown
    logger.info("Server shutting down...")


app = FastAPI(
    title="ChronicAI API",
    description="Local-first telemedicine application for chronic patients and doctors in Vietnam",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload_router)
app.include_router(chat_router)
app.include_router(doctor_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "ChronicAI",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "upload": "/upload",
            "chat": "/chat",
            "doctor": "/doctor"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with model availability."""
    from app.services.llm import check_system_health
    
    try:
        system_status = await check_system_health()
        return {
            "status": system_status["status"],
            "api": "healthy",
            "llm_provider": system_status.get("provider", settings.llm_provider),
            "llm": system_status.get("llm", False),
            "ollama": system_status.get("ollama", False),
            "models": system_status.get("models", {}),
            "message": system_status.get("message", "")
        }
    except Exception as e:
        return {
            "status": "degraded",
            "api": "healthy",
            "llm_provider": settings.llm_provider,
            "llm": False,
            "ollama": False,
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        reload=True
    )
