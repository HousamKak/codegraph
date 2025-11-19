"""Indexing endpoints."""

import os
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from codegraph import PythonParser, GraphBuilder
from ..database import get_db
from ..models import SuccessResponse


class FileIndexRequest(BaseModel):
    """Request to index a single file."""
    file_path: str
    clear: bool = False


class DirectoryIndexRequest(BaseModel):
    """Request to index a directory."""
    directory: str
    clear: bool = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/index", tags=["Indexing"])


@router.post("", response_model=SuccessResponse)
async def index_code(request: FileIndexRequest):
    """
    Index Python code into the graph database.

    After editing files with your LLM tools, call this to update the graph.
    """
    db = get_db()
    parser = PythonParser()
    builder = GraphBuilder(db)

    try:
        abs_path = os.path.abspath(request.file_path)

        if request.clear:
            db.clear_database()
        else:
            db.delete_nodes_from_file(abs_path)

        entities, relationships = parser.parse_file(abs_path)
        builder.build_graph(entities, relationships)

        return SuccessResponse(
            success=True,
            message=f"Indexed {len(entities)} entities and {len(relationships)} relationships",
            data={
                "file": request.file_path,
                "entities": len(entities),
                "relationships": len(relationships)
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/directory", response_model=SuccessResponse)
async def index_directory(request: DirectoryIndexRequest):
    """
    Index all Python files in a directory.

    Recursively indexes .py files, skipping common non-code directories.
    """
    db = get_db()
    parser = PythonParser()
    builder = GraphBuilder(db)

    try:
        directory = os.path.abspath(request.directory)

        if request.clear:
            db.clear_database()
        else:
            db.delete_nodes_from_file(directory)

        entities, relationships = parser.parse_directory(directory)
        builder.build_graph(entities, relationships)

        return SuccessResponse(
            success=True,
            message=f"Indexed directory with {len(entities)} entities and {len(relationships)} relationships",
            data={
                "directory": request.directory,
                "entities": len(entities),
                "relationships": len(relationships)
            }
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.directory}")
    except Exception as e:
        logger.error(f"Directory indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear", response_model=SuccessResponse)
async def clear_graph():
    """
    Clear all data from the graph database.

    Use with caution - this removes all indexed code.
    """
    db = get_db()

    try:
        db.clear_database()
        return SuccessResponse(
            success=True,
            message="Graph database cleared"
        )
    except Exception as e:
        logger.error(f"Clear graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
