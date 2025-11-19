"""API endpoints for controlling file watching."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio
import logging

from ..services import get_realtime_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/watch", tags=["watch"])


class WatchRequest(BaseModel):
    """Request to start watching a directory."""
    directory: str


class WatchStatus(BaseModel):
    """Status of file watching."""
    enabled: bool
    directory: str | None = None


@router.post("/start")
async def start_watching(request: WatchRequest):
    """
    Start watching a directory for file changes.

    When enabled, the backend will automatically:
    1. Detect Python file changes
    2. Re-index changed files
    3. Propagate changes to dependent nodes
    4. Validate using conservation laws
    5. Broadcast updates via WebSocket
    """
    service = get_realtime_service()
    if not service:
        raise HTTPException(status_code=500, detail="Realtime service not initialized")

    try:
        # Get the current event loop
        loop = asyncio.get_event_loop()

        # Start watching
        service.start_watching(request.directory, loop)

        return {
            "success": True,
            "message": f"Started watching directory: {request.directory}",
            "directory": request.directory
        }

    except Exception as e:
        logger.error(f"Error starting file watcher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_watching():
    """Stop watching for file changes."""
    service = get_realtime_service()
    if not service:
        raise HTTPException(status_code=500, detail="Realtime service not initialized")

    try:
        service.stop_watching()

        return {
            "success": True,
            "message": "Stopped watching for file changes"
        }

    except Exception as e:
        logger.error(f"Error stopping file watcher: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=WatchStatus)
async def get_watch_status():
    """Get the current file watching status."""
    service = get_realtime_service()
    if not service:
        return WatchStatus(enabled=False, directory=None)

    return WatchStatus(
        enabled=service.is_watching(),
        directory=service.watch_directory
    )
