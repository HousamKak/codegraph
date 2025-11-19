"""Function analysis endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException
import logging

from ..database import get_db, get_query
from ..models import (
    FunctionResponse, FunctionSignatureResponse, CallerResponse,
    CalleeResponse, DependenciesResponse, GraphResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/functions", tags=["Function Analysis"])


@router.get("", response_model=List[FunctionResponse])
async def list_functions(skip: int = 0, limit: int = 100):
    """List all functions in the codebase."""
    db = get_db()

    try:
        functions = db.get_all_functions(skip=skip, limit=limit)
        return functions
    except Exception as e:
        logger.error(f"List functions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}", response_model=FunctionResponse)
async def get_function(function_id: str):
    """Get a specific function by ID."""
    db = get_db()

    try:
        function = db.get_function_by_id(function_id)
        if not function:
            raise HTTPException(status_code=404, detail="Function not found")
        return function
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get function failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}/signature", response_model=FunctionSignatureResponse)
async def get_function_signature(function_id: str):
    """Get the signature of a function including parameters and return type."""
    query_interface = get_query()

    try:
        signature = query_interface.get_function_signature(function_id)
        if not signature:
            raise HTTPException(status_code=404, detail="Function not found")
        return signature
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get function signature failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}/callers", response_model=List[CallerResponse])
async def get_function_callers(function_id: str):
    """Get all functions that call this function."""
    query_interface = get_query()

    try:
        callers = query_interface.get_callers(function_id)
        return callers
    except Exception as e:
        logger.error(f"Get function callers failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}/callees", response_model=List[CalleeResponse])
async def get_function_callees(function_id: str):
    """Get all functions that this function calls."""
    query_interface = get_query()

    try:
        callees = query_interface.get_callees(function_id)
        return callees
    except Exception as e:
        logger.error(f"Get function callees failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}/dependencies", response_model=DependenciesResponse)
async def get_function_dependencies(function_id: str, depth: int = 2):
    """Get the dependency graph for a function."""
    query_interface = get_query()

    try:
        dependencies = query_interface.get_dependencies(function_id, depth=depth)
        return dependencies
    except Exception as e:
        logger.error(f"Get function dependencies failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{function_id}/graph", response_model=GraphResponse)
async def get_function_graph(function_id: str, depth: int = 1):
    """Get the subgraph centered on a function."""
    db = get_db()

    try:
        result = db.get_function_subgraph(function_id, depth=depth)
        if not result:
            raise HTTPException(status_code=404, detail="Function not found")
        return GraphResponse(
            nodes=result.get("nodes", []),
            edges=result.get("edges", [])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get function graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
