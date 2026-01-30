from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import upload_router, chat_router, doctor_router

app = FastAPI(
    title="ChronicAI API",
    description="Local-first telemedicine application for chronic patients and doctors in Vietnam",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
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
            "ollama": system_status.get("ollama", False),
            "models": system_status.get("models", {}),
            "message": system_status.get("message", "")
        }
    except Exception as e:
        return {
            "status": "degraded",
            "api": "healthy",
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
