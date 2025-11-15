"""FastAPI backend for CodeGraph - Read-Only Analysis API."""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from codegraph import PythonParser, GraphBuilder
from .config import settings
from .database import db_manager, get_db, get_query, get_validator, get_snapshot_manager
from .models import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup
    logger.info("Starting CodeGraph Backend (Read-Only Analysis Mode)...")
    db_manager.connect()
    logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
    yield
    # Shutdown
    logger.info("Shutting down CodeGraph Backend...")
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


# Indexing Endpoints

@app.post("/index", response_model=SuccessResponse)
async def index_code(request: IndexRequest):
    """
    Index Python code into the graph database.

    After editing files with your LLM tools, call this to update the graph.
    """
    db = get_db()
    parser = PythonParser()
    builder = GraphBuilder(db)

    try:
        # Clear database if requested
        if request.clear:
            db.clear_database()
            logger.info("Database cleared")
        else:
            # When not clearing, delete nodes from the specific file(s) being re-indexed
            if os.path.isfile(request.path):
                db.delete_nodes_from_file(request.path)
                logger.info(f"Deleted existing nodes from {request.path}")
            # For directories, we'll rely on MERGE to update existing nodes

        # Initialize schema
        db.initialize_schema()

        # Parse code
        if os.path.isfile(request.path):
            entities, relationships = parser.parse_file(request.path)
        elif os.path.isdir(request.path):
            entities, relationships = parser.parse_directory(request.path)
        else:
            raise HTTPException(status_code=400, detail=f"Path must be a file or directory")

        # Build graph
        builder.build_graph(entities, relationships)

        # Get statistics
        stats = db.get_statistics()

        return SuccessResponse(
            success=True,
            message=f"Indexed {request.path}",
            data={
                "entities": len(entities),
                "relationships": len(relationships),
                "stats": stats
            }
        )

    except Exception as e:
        logger.error(f"Indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear", response_model=SuccessResponse)
async def clear_database():
    """Clear all data from the database."""
    db = get_db()
    try:
        db.clear_database()
        return SuccessResponse(
            success=True,
            message="Database cleared successfully"
        )
    except Exception as e:
        logger.error(f"Clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Query Endpoints

@app.get("/functions", response_model=List[FunctionResponse])
async def find_functions(name: str = None, qualified_name: str = None):
    """Find functions by name or qualified name."""
    query = get_query()
    try:
        results = query.find_function(name=name, qualified_name=qualified_name)
        return [FunctionResponse(**r) for r in results]
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/signature", response_model=FunctionSignatureResponse)
async def get_function_signature(function_id: str):
    """Get function signature with parameters."""
    query = get_query()
    try:
        result = query.get_function_signature(function_id)
        if not result:
            raise HTTPException(status_code=404, detail="Function not found")

        return FunctionSignatureResponse(
            function=result["function"],
            parameters=result["parameters"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/callers", response_model=List[CallerResponse])
async def get_function_callers(function_id: str):
    """Find all functions that call this function."""
    query = get_query()
    try:
        callers = query.find_callers(function_id)
        return [
            CallerResponse(
                caller=c["caller"],
                arg_count=c.get("arg_count"),
                location=c.get("location")
            )
            for c in callers
        ]
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/callees", response_model=List[CalleeResponse])
async def get_function_callees(function_id: str):
    """Find all functions called by this function."""
    query = get_query()
    try:
        callees = query.find_callees(function_id)
        return [
            CalleeResponse(
                callee=c["callee"],
                arg_count=c.get("arg_count"),
                location=c.get("location")
            )
            for c in callees
        ]
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/dependencies", response_model=DependenciesResponse)
async def get_function_dependencies(function_id: str, depth: int = 1):
    """Get complete dependency graph for a function."""
    query = get_query()
    try:
        deps = query.get_function_dependencies(function_id, depth)
        return DependenciesResponse(
            outbound=deps["outbound"],
            inbound=deps["inbound"]
        )
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search & Analysis Endpoints

@app.post("/search", response_model=List[NodeResponse])
async def search_by_pattern(request: SearchRequest):
    """Search for entities by name pattern."""
    query = get_query()
    try:
        entity_type_str = request.entity_type.value if request.entity_type else None
        results = query.search_by_pattern(request.pattern, entity_type_str)
        return [
            NodeResponse(
                id=r["node"]["id"],
                labels=r["labels"],
                properties=r["node"]
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    Analyze the impact of changing or deleting an entity.

    Use this BEFORE editing code to understand what will be affected.
    """
    query = get_query()
    try:
        impact = query.get_impact_analysis(request.entity_id, request.change_type)
        return ImpactAnalysisResponse(
            entity_id=impact["entity_id"],
            change_type=impact["change_type"],
            affected_callers=impact["affected_callers"],
            affected_references=impact["affected_references"],
            cascading_changes=impact.get("cascading_changes", [])
        )
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Validation Endpoints

@app.get("/validate", response_model=ValidationReportResponse)
async def validate_code():
    """
    Validate all conservation laws.

    Call this AFTER editing code to check if anything broke.
    Returns detailed violations with file paths, line numbers, and code snippets.
    """
    validator = get_validator()
    try:
        violations = validator.validate_all()

        # Group by severity
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        # Group by type
        by_type = {}
        for v in violations:
            vtype = v.violation_type.value
            by_type[vtype] = by_type.get(vtype, 0) + 1

        # Convert to response format
        violation_responses = [
            ViolationResponse(
                violation_type=v.violation_type.value,
                severity=v.severity,
                entity_id=v.entity_id,
                message=v.message,
                details=v.details,
                suggested_fix=v.suggested_fix,
                file_path=v.file_path,
                line_number=v.line_number,
                column_number=v.column_number,
                old_value=v.old_value,
                new_value=v.new_value,
                code_snippet=v.code_snippet
            )
            for v in violations
        ]

        return ValidationReportResponse(
            total_violations=len(violations),
            errors=len(errors),
            warnings=len(warnings),
            by_type=by_type,
            summary={
                "signature_conservation": sum(1 for v in violations if v.violation_type.value == "signature_mismatch"),
                "reference_integrity": sum(1 for v in violations if v.violation_type.value == "reference_broken"),
                "data_flow_consistency": sum(1 for v in violations if v.violation_type.value == "data_flow_invalid"),
                "structural_integrity": sum(1 for v in violations if v.violation_type.value == "structural_invalid")
            },
            violations=violation_responses
        )

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Graph Export for Visualization

@app.get("/graph", response_model=GraphResponse)
async def get_graph_data(limit: int = 100):
    """
    Export graph data for visualization.

    Returns nodes and edges in a format suitable for D3.js, Cytoscape.js, etc.
    """
    db = get_db()
    try:
        # Get nodes (limited)
        nodes_query = f"MATCH (n) RETURN n, labels(n) as labels LIMIT {limit}"
        node_results = db.execute_query(nodes_query)

        nodes = []
        node_ids = set()
        for r in node_results:
            node = dict(r["n"])
            node_id = node.get("id")
            if node_id:
                node_ids.add(node_id)
                nodes.append({
                    "id": node_id,
                    "labels": r["labels"],
                    "properties": node
                })

        # Get edges between these nodes
        edges_query = """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        """
        edge_results = db.execute_query(edges_query, {"node_ids": list(node_ids)})

        edges = []
        for r in edge_results:
            edges.append({
                "source": r["source"],
                "target": r["target"],
                "type": r["rel_type"],
                "properties": r["props"]
            })

        return GraphResponse(
            nodes=nodes,
            edges=edges
        )

    except Exception as e:
        logger.error(f"Graph export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/function/{function_id}", response_model=GraphResponse)
async def get_function_subgraph(function_id: str, depth: int = 1):
    """Get subgraph around a specific function."""
    db = get_db()
    try:
        # Get function and its neighbors up to depth
        nodes_query = f"""
        MATCH path = (f:Function {{id: $function_id}})-[*0..{depth}]-(n)
        RETURN DISTINCT n, labels(n) as labels
        """
        node_results = db.execute_query(nodes_query, {"function_id": function_id})

        nodes = []
        node_ids = set()
        for r in node_results:
            node = dict(r["n"])
            node_id = node.get("id")
            if node_id:
                node_ids.add(node_id)
                nodes.append({
                    "id": node_id,
                    "labels": r["labels"],
                    "properties": node
                })

        # Get edges
        edges_query = """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        """
        edge_results = db.execute_query(edges_query, {"node_ids": list(node_ids)})

        edges = []
        for r in edge_results:
            edges.append({
                "source": r["source"],
                "target": r["target"],
                "type": r["rel_type"],
                "properties": r["props"]
            })

        return GraphResponse(
            nodes=nodes,
            edges=edges
        )

    except Exception as e:
        logger.error(f"Subgraph export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Custom Query Endpoint (Advanced)

@app.post("/query")
async def execute_custom_query(request: CypherQueryRequest):
    """
    Execute a custom Cypher query.

    WARNING: This is a raw query interface. Use with caution.
    """
    db = get_db()
    try:
        results = db.execute_query(request.query, request.parameters or {})
        return results
    except Exception as e:
        logger.error(f"Custom query failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Snapshot Endpoints

@app.post("/snapshot/create")
async def create_snapshot(description: str = ""):
    """
    Create a snapshot of the current graph state.
    
    Use this BEFORE editing code to capture the current state.
    Then edit code, re-index, and compare snapshots to detect what changed.
    """
    snapshot_mgr = get_snapshot_manager()
    
    try:
        snapshot_id = snapshot_mgr.create_snapshot(description)
        snapshot = snapshot_mgr.get_snapshot_data(snapshot_id)
        
        return {
            "snapshot_id": snapshot_id,
            "description": description,
            "node_count": snapshot["node_count"],
            "edge_count": snapshot["edge_count"],
            "timestamp": snapshot["timestamp"]
        }
    except Exception as e:
        logger.error(f"Snapshot creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: str):
    """Get details about a specific snapshot."""
    snapshot_mgr = get_snapshot_manager()
    
    try:
        snapshot = snapshot_mgr.get_snapshot_data(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        return {
            "snapshot_id": snapshot_id,
            "description": snapshot.get("description", ""),
            "timestamp": snapshot["timestamp"],
            "node_count": snapshot["node_count"],
            "edge_count": snapshot["edge_count"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/snapshot/compare")
async def compare_snapshots(old_snapshot_id: str, new_snapshot_id: str):
    """
    Compare two snapshots to detect changes.
    
    Returns detailed diff showing:
    - Nodes added, removed, modified
    - Edges added, removed, modified
    - Summary statistics
    
    Use this after editing and re-indexing to see what changed.
    """
    snapshot_mgr = get_snapshot_manager()
    
    try:
        diff = snapshot_mgr.compare_snapshots(old_snapshot_id, new_snapshot_id)
        
        return {
            "old_snapshot_id": old_snapshot_id,
            "new_snapshot_id": new_snapshot_id,
            "summary": {
                "nodes_added": len(diff.nodes.added),
                "nodes_removed": len(diff.nodes.removed),
                "nodes_modified": len(diff.nodes.modified),
                "edges_added": len(diff.edges.added),
                "edges_removed": len(diff.edges.removed),
                "edges_modified": len(diff.edges.modified)
            },
            "nodes": {
                "added": diff.nodes.added,
                "removed": diff.nodes.removed,
                "modified": diff.nodes.modified
            },
            "edges": {
                "added": diff.edges.added,
                "removed": diff.edges.removed,
                "modified": diff.edges.modified
            }
        }
    except Exception as e:
        logger.error(f"Snapshot comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/snapshots")
async def list_snapshots():
    """List all available snapshots."""
    snapshot_mgr = get_snapshot_manager()
    
    try:
        snapshots = snapshot_mgr.list_snapshots()
        return {
            "snapshots": [
                {
                    "snapshot_id": s.snapshot_id,
                    "description": s.description,
                    "timestamp": s.timestamp,
                    "node_count": s.node_count,
                    "edge_count": s.edge_count
                }
                for s in snapshots
            ],
            "count": len(snapshots)
        }
    except Exception as e:
        logger.error(f"List snapshots failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
