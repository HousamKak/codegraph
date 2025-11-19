"""Git commit-based snapshot endpoints."""

from fastapi import APIRouter, HTTPException
import logging

from ..database import get_git_snapshot_manager
from ..models import GraphResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/commits", tags=["Git Commits"])


@router.get("")
async def list_commits(limit: int = 50):
    """
    List git commits (automatic snapshots).

    Each commit represents a potential snapshot of the codebase graph.
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(
            status_code=400,
            detail="Git snapshot manager not initialized. Set REPO_PATH or ensure current directory is a git repo."
        )

    try:
        commits = git_mgr.list_commits(limit=limit)
        return {
            "commits": [
                {
                    "hash": c.hash,
                    "short_hash": c.short_hash,
                    "message": c.message,
                    "author": c.author,
                    "date": c.date,
                    "indexed": c.indexed
                }
                for c in commits
            ],
            "count": len(commits)
        }
    except Exception as e:
        logger.error(f"List commits failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{commit_hash}")
async def get_commit(commit_hash: str):
    """Get information about a specific commit."""
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        commit = git_mgr.get_commit_info(commit_hash)
        if not commit:
            raise HTTPException(status_code=404, detail="Commit not found")

        files_changed = git_mgr.get_files_changed_in_commit(commit_hash)

        return {
            "hash": commit.hash,
            "short_hash": commit.short_hash,
            "message": commit.message,
            "author": commit.author,
            "date": commit.date,
            "indexed": commit.indexed,
            "files_changed": files_changed
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get commit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{commit_hash}/index")
async def index_commit(commit_hash: str):
    """
    Index code at a specific commit.

    This parses all Python files at the given commit and stores the graph.
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        result = git_mgr.index_commit(commit_hash)
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Index commit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{commit_hash}/graph", response_model=GraphResponse)
async def get_commit_graph(commit_hash: str):
    """
    Get graph data for a specific commit.

    If the commit hasn't been indexed yet, it will be indexed automatically.
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        graph = git_mgr.get_snapshot_graph(commit_hash)
        return GraphResponse(
            nodes=graph.get("nodes", []),
            edges=graph.get("edges", [])
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get commit graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff")
async def compare_commits(old: str, new: str):
    """
    Compare two commits and return differences.

    Both commits will be indexed if not already.
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        diff = git_mgr.compare_commits(old, new)
        return diff
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Compare commits failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff/file")
async def get_file_diff(old: str, new: str, filepath: str):
    """
    Get text diff for a specific file between two commits.

    Args:
        old: Old commit hash
        new: New commit hash
        filepath: Path to the file

    Returns:
        Unified diff content with stats
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        diff = git_mgr.get_file_diff(old, new, filepath)
        return diff
    except Exception as e:
        logger.error(f"Get file diff failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diff/files")
async def list_changed_files(old: str, new: str):
    """
    List all files changed between two commits with their stats.

    Args:
        old: Old commit hash
        new: New commit hash

    Returns:
        List of changed files with addition/deletion counts
    """
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        files = git_mgr.list_changed_files(old, new)
        return {
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        logger.error(f"List changed files failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{commit_hash}/snapshot")
async def delete_commit_snapshot(commit_hash: str):
    """Delete the indexed snapshot for a commit."""
    git_mgr = get_git_snapshot_manager()

    if not git_mgr:
        raise HTTPException(status_code=400, detail="Git snapshot manager not initialized")

    try:
        deleted = git_mgr.delete_snapshot(commit_hash)
        return {
            "success": True,
            "message": "Snapshot deleted" if deleted else "Snapshot not found",
            "deleted": deleted
        }
    except Exception as e:
        logger.error(f"Delete commit snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
