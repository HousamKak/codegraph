"""Graph query endpoints."""

from fastapi import APIRouter, HTTPException
import logging

from ..database import get_db
from ..models import GraphResponse, CypherQueryRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/graph", tags=["Graph Queries"])


@router.get("", response_model=GraphResponse)
async def get_graph(limit: int = 100):
    """
    Get graph data (nodes and edges).

    Returns nodes and edges from the current graph state.
    """
    db = get_db()

    try:
        nodes = db.get_all_nodes(limit=limit)
        edges = db.get_all_edges(limit=limit * 2)
        return GraphResponse(nodes=nodes, edges=edges)
    except Exception as e:
        logger.error(f"Get graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_query(request: CypherQueryRequest):
    """
    Execute a Cypher query on the graph.

    For read-only queries to explore the codebase structure.
    """
    db = get_db()

    try:
        results = db.execute_query(request.query, request.parameters or {})
        return {
            "rows": results,
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_id}", response_model=GraphResponse)
async def get_node(node_id: str):
    """Get a specific node by ID with its immediate relationships."""
    db = get_db()

    try:
        node = db.get_node_by_id(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")

        edges = db.get_node_edges(node_id)

        return GraphResponse(nodes=[node], edges=edges)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get node failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/node/{node_id}/neighbors", response_model=GraphResponse)
async def get_node_neighbors(node_id: str, depth: int = 1):
    """Get a node and its neighbors up to specified depth."""
    db = get_db()

    try:
        result = db.get_node_neighborhood(node_id, depth=depth)
        return GraphResponse(
            nodes=result.get("nodes", []),
            edges=result.get("edges", [])
        )
    except Exception as e:
        logger.error(f"Get node neighbors failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_graph_statistics():
    """Get graph statistics (node/edge counts by type)."""
    db = get_db()

    try:
        stats = db.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_nodes(q: str, node_type: str = None, limit: int = 50):
    """Search for nodes by name or properties."""
    db = get_db()

    try:
        results = db.search_nodes(pattern=q, node_type=node_type, limit=limit)
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
