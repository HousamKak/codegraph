"""Analysis endpoints (search, impact analysis)."""

from typing import List
from fastapi import APIRouter, HTTPException
import logging

from ..database import get_db, get_query
from ..models import (
    SearchRequest, NodeResponse, ImpactAnalysisRequest, ImpactAnalysisResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/search", response_model=List[NodeResponse])
async def search_nodes(request: SearchRequest):
    """
    Search for nodes by name or pattern.

    Supports fuzzy matching and filtering by node type.
    """
    db = get_db()

    try:
        results = db.search_nodes(
            pattern=request.pattern,
            node_type=request.entity_type.value if request.entity_type else None,
            limit=request.limit
        )
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    Analyze the impact of changing an entity.

    Returns all affected callers, references, and cascading changes.
    """
    query_interface = get_query()

    try:
        impact = query_interface.get_impact_analysis(
            entity_id=request.entity_id,
            change_type=request.change_type.value
        )
        return impact
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
