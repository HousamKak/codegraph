"""Legacy snapshot endpoints (manual snapshots)."""

from fastapi import APIRouter, HTTPException
import logging

from ..database import get_snapshot_manager
from ..models import GraphResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/snapshots", tags=["Snapshots (Legacy)"])


@router.get("")
async def list_snapshots():
    """List all snapshots."""
    snapshot_mgr = get_snapshot_manager()

    try:
        snapshots = snapshot_mgr.list_snapshots()
        return {
            "snapshots": snapshots,
            "count": len(snapshots)
        }
    except Exception as e:
        logger.error(f"List snapshots failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create")
async def create_snapshot(description: str = ""):
    """Create a new snapshot of current graph state."""
    snapshot_mgr = get_snapshot_manager()

    try:
        snapshot_id = snapshot_mgr.create_snapshot(description=description)
        return {"snapshot_id": snapshot_id}
    except Exception as e:
        logger.error(f"Create snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """Get snapshot metadata and statistics."""
    snapshot_mgr = get_snapshot_manager()

    try:
        snapshot = snapshot_mgr.get_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        return snapshot
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{snapshot_id}/graph", response_model=GraphResponse)
async def get_snapshot_graph(snapshot_id: str):
    """Get graph data from a snapshot."""
    snapshot_mgr = get_snapshot_manager()

    try:
        graph = snapshot_mgr.get_snapshot_graph(snapshot_id)
        if not graph:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        return GraphResponse(
            nodes=graph.get("nodes", []),
            edges=graph.get("edges", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get snapshot graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{snapshot_id}")
async def delete_snapshot(snapshot_id: str):
    """Delete a snapshot."""
    snapshot_mgr = get_snapshot_manager()

    try:
        deleted = snapshot_mgr.delete_snapshot(snapshot_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        return {"success": True, "message": "Snapshot deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare")
async def compare_snapshots(old_snapshot_id: str, new_snapshot_id: str):
    """Compare two snapshots and return differences."""
    snapshot_mgr = get_snapshot_manager()

    try:
        diff = snapshot_mgr.compare_snapshots(old_snapshot_id, new_snapshot_id)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Compare snapshots failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
