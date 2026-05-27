import os
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

# Load environment variables
load_dotenv()

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.JSONRenderer(),
    ]
)
logger = structlog.get_logger()

from src.presentation.app import lifespan

def create_app() -> FastAPI:
    app = FastAPI(
        title="ResumeRank Pro",
        description="Production ATS scoring API",
        version="1.1.0",
        lifespan=lifespan
    )

    # 1. FIX: Robust CORS for Mobile Access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # 4. Debug Middleware: Log Mobile IP & Request Details
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        client_host = request.client.host if request.client else "unknown"
        logger.info("incoming_request", method=request.method, path=request.url.path, ip=client_host)
        
        response = await call_next(request)
        return response

    # 2. Global Error Handling
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(exc)}"}
        )

    # 3. Health Check
    @app.get("/health")
    async def health():
        return {"status": "ok", "message": "Resume Rank Backend is active"}

    # Import routes here to avoid circular imports
    from src.presentation.api.v1 import analyze, status, health as health_route, gdpr, skills, rewrite, insights, auth
    app.include_router(analyze.router, prefix="/v1")
    app.include_router(status.router, prefix="/v1")
    app.include_router(health_route.router, prefix="/v1")
    app.include_router(gdpr.router, prefix="/v1")
    app.include_router(skills.router, prefix="/v1")
    app.include_router(rewrite.router, prefix="/v1")
    app.include_router(insights.router, prefix="/v1")
    app.include_router(auth.router, prefix="/v1")

    return app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9000))
    print(f"Starting Backend on 0.0.0.0:{port}")
    print(f"For Mobile: Use your Computer's IP instead of localhost")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
