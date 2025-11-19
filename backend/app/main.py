"""FastAPI backend for CodeGraph - Read-Only Analysis API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from .config import settings
from .database import db_manager, get_db
from .models import SuccessResponse, HealthResponse, StatisticsResponse
from .routers import (
    graph_router, commits_router, validation_router, index_router,
    snapshots_router, functions_router, analysis_router, files_router,
    websocket_router, watch_router
)
from .services import RealtimeGraphService, set_realtime_service, get_realtime_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup
    logger.info("Starting CodeGraph Backend with Real-Time Updates...")
    db_manager.connect()
    logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")

    # Initialize realtime service
    realtime_service = RealtimeGraphService(get_db())
    set_realtime_service(realtime_service)
    logger.info("Real-time service initialized (file watching disabled by default)")

    yield

    # Shutdown
    logger.info("Shutting down CodeGraph Backend...")

    # Stop file watching if active
    if get_realtime_service() and get_realtime_service().is_watching():
        get_realtime_service().stop_watching()

    db_manager.disconnect()


# Create FastAPI app
app = FastAPI(
    title="CodeGraph API",
    description="REST API for CodeGraph - Read-Only Code Analysis with Graph Database",
    version="0.2.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(websocket_router)  # WebSocket first for real-time updates
app.include_router(watch_router)  # File watching control
app.include_router(files_router)
app.include_router(graph_router)
app.include_router(commits_router)
app.include_router(validation_router)
app.include_router(index_router)
app.include_router(snapshots_router)
app.include_router(functions_router)
app.include_router(analysis_router)


# Health & Info Endpoints

@app.get("/", response_model=SuccessResponse)
async def root():
    """Root endpoint."""
    return SuccessResponse(
        success=True,
        message="CodeGraph API - Read-Only Analysis Mode",
        data={
            "version": "0.2.0",
            "mode": "read-only",
            "description": "This API provides code analysis tools. Use your LLM's file editing tools to modify code, then use this API to analyze relationships and validate changes."
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    db = get_db()
    try:
        stats = db.get_statistics()
        return HealthResponse(
            status="healthy",
            database_connected=True,
            neo4j_uri=settings.neo4j_uri
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            neo4j_uri=settings.neo4j_uri
        )


@app.get("/stats", response_model=StatisticsResponse)
async def get_statistics():
    """Get database statistics."""
    db = get_db()
    stats = db.get_statistics()
    return StatisticsResponse(stats=stats)
