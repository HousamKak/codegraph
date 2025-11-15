"""FastAPI backend for CodeGraph."""

import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from codegraph import PythonParser, GraphBuilder
from .config import settings
from .database import db_manager, get_db, get_query, get_validator
from .models import *

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup
    logger.info("Starting CodeGraph Backend...")
    db_manager.connect()
    logger.info(f"Connected to Neo4j at {settings.neo4j_uri}")
    yield
    # Shutdown
    logger.info("Shutting down CodeGraph Backend...")
    db_manager.disconnect()


# Create FastAPI app
app = FastAPI(
    title="CodeGraph API",
    description="REST API for CodeGraph - A graph database for Python codebases",
    version="0.1.0",
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
        message="CodeGraph API is running",
        data={"version": "0.1.0"}
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if db_manager.is_connected() else "unhealthy",
        database_connected=db_manager.is_connected(),
        neo4j_uri=settings.neo4j_uri
    )


@app.get("/stats", response_model=StatisticsResponse)
async def get_statistics():
    """Get database statistics."""
    try:
        db = get_db()
        stats = db.get_statistics()
        return StatisticsResponse(stats=stats)
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Indexing Endpoints

@app.post("/index", response_model=SuccessResponse)
async def index_codebase(request: IndexRequest):
    """Index a Python file or directory."""
    try:
        db = get_db()

        # Clear database if requested
        if request.clear:
            logger.info("Clearing database...")
            db.clear_database()

        # Initialize schema
        db.initialize_schema()

        # Parse code
        logger.info(f"Parsing {request.path}...")
        parser = PythonParser()

        if os.path.isfile(request.path):
            entities, relationships = parser.parse_file(request.path)
        elif os.path.isdir(request.path):
            entities, relationships = parser.parse_directory(request.path)
        else:
            raise HTTPException(status_code=400, detail="Path must be a file or directory")

        # Build graph
        logger.info(f"Building graph with {len(entities)} entities...")
        builder = GraphBuilder(db)
        builder.build_graph(entities, relationships)

        # Get stats
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
        logger.error(f"Error indexing codebase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/clear", response_model=SuccessResponse)
async def clear_database():
    """Clear the entire database."""
    try:
        db = get_db()
        db.clear_database()
        return SuccessResponse(
            success=True,
            message="Database cleared"
        )
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Function Query Endpoints

@app.get("/functions", response_model=List[FunctionResponse])
async def get_functions(name: Optional[str] = None, qualified_name: Optional[str] = None):
    """Get functions by name or qualified name."""
    try:
        query = get_query()
        functions = query.find_function(name=name, qualified_name=qualified_name)
        return [FunctionResponse(**func) for func in functions]
    except Exception as e:
        logger.error(f"Error getting functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/signature", response_model=FunctionSignatureResponse)
async def get_function_signature(function_id: str):
    """Get function signature with parameters."""
    try:
        query = get_query()
        sig_info = query.get_function_signature(function_id)

        if not sig_info:
            raise HTTPException(status_code=404, detail="Function not found")

        return FunctionSignatureResponse(
            function=FunctionResponse(**sig_info['function']),
            parameters=[ParameterResponse(**p['param']) for p in sig_info['parameters']]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting function signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/callers", response_model=List[CallerResponse])
async def get_callers(function_id: str):
    """Get all functions that call this function."""
    try:
        query = get_query()
        callers = query.find_callers(function_id)
        return [
            CallerResponse(
                caller=FunctionResponse(**c['caller']),
                arg_count=c.get('arg_count'),
                location=c.get('location')
            )
            for c in callers
        ]
    except Exception as e:
        logger.error(f"Error getting callers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/callees", response_model=List[CalleeResponse])
async def get_callees(function_id: str):
    """Get all functions called by this function."""
    try:
        query = get_query()
        callees = query.find_callees(function_id)
        return [
            CalleeResponse(
                callee=FunctionResponse(**c['callee']),
                arg_count=c.get('arg_count'),
                location=c.get('location')
            )
            for c in callees
        ]
    except Exception as e:
        logger.error(f"Error getting callees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/functions/{function_id}/dependencies", response_model=DependenciesResponse)
async def get_dependencies(function_id: str, depth: int = 1):
    """Get function dependencies."""
    try:
        query = get_query()
        deps = query.get_function_dependencies(function_id, depth)

        return DependenciesResponse(
            inbound=[
                DependencyResponse(
                    function=FunctionResponse(**d['function']),
                    distance=d['distance']
                )
                for d in deps['inbound']
            ],
            outbound=[
                DependencyResponse(
                    function=FunctionResponse(**d['function']),
                    distance=d['distance']
                )
                for d in deps['outbound']
            ]
        )
    except Exception as e:
        logger.error(f"Error getting dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search & Discovery Endpoints

@app.post("/search", response_model=List[NodeResponse])
async def search_entities(request: SearchRequest):
    """Search for entities by pattern."""
    try:
        query = get_query()
        results = query.search_by_pattern(
            request.pattern,
            request.entity_type.value if request.entity_type else None
        )

        return [
            NodeResponse(
                id=r['node']['id'],
                labels=r['labels'],
                properties=r['node']
            )
            for r in results
        ]
    except Exception as e:
        logger.error(f"Error searching entities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Impact Analysis Endpoints

@app.post("/impact", response_model=ImpactAnalysisResponse)
async def analyze_impact(request: ImpactAnalysisRequest):
    """Analyze the impact of changing an entity."""
    try:
        query = get_query()
        impact = query.get_impact_analysis(request.entity_id, request.change_type.value)

        return ImpactAnalysisResponse(**impact)
    except Exception as e:
        logger.error(f"Error analyzing impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Validation Endpoints

@app.get("/validate", response_model=ValidationReportResponse)
async def validate_codebase():
    """Validate codebase against conservation laws."""
    try:
        validator = get_validator()
        report = validator.get_validation_report()

        return ValidationReportResponse(
            total_violations=report['total_violations'],
            errors=report['errors'],
            warnings=report['warnings'],
            by_type=report['by_type'],
            summary=report['summary'],
            violations=[
                ViolationResponse(
                    violation_type=v.violation_type.value,
                    severity=ViolationSeverity(v.severity),
                    entity_id=v.entity_id,
                    message=v.message,
                    details=v.details,
                    suggested_fix=v.suggested_fix
                )
                for v in report['violations']
            ]
        )
    except Exception as e:
        logger.error(f"Error validating codebase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate/change", response_model=List[ViolationResponse])
async def validate_change(request: ValidateChangeRequest):
    """Validate a proposed change."""
    try:
        validator = get_validator()
        violations = validator.validate_change(
            request.entity_id,
            request.change_type.value,
            request.new_properties
        )

        return [
            ViolationResponse(
                violation_type=v.violation_type.value,
                severity=ViolationSeverity(v.severity),
                entity_id=v.entity_id,
                message=v.message,
                details=v.details,
                suggested_fix=v.suggested_fix
            )
            for v in violations
        ]
    except Exception as e:
        logger.error(f"Error validating change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Graph Visualization Endpoints

@app.get("/graph", response_model=GraphResponse)
async def get_full_graph(limit: int = 100):
    """Get the complete graph for visualization (limited)."""
    try:
        db = get_db()

        # Get nodes
        nodes_query = f"MATCH (n) RETURN n LIMIT {limit}"
        node_results = db.execute_query(nodes_query)

        nodes = [
            NodeResponse(
                id=r['n']['id'],
                labels=['Unknown'],  # Labels not easily available in dict form
                properties=dict(r['n'])
            )
            for r in node_results
        ]

        # Get edges
        edges_query = f"MATCH (a)-[r]->(b) RETURN a.id as source, type(r) as type, b.id as target, properties(r) as props LIMIT {limit * 2}"
        edge_results = db.execute_query(edges_query)

        edges = [
            EdgeResponse(
                source=r['source'],
                target=r['target'],
                type=r['type'],
                properties=r['props']
            )
            for r in edge_results
        ]

        return GraphResponse(nodes=nodes, edges=edges)
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/function/{function_id}", response_model=GraphResponse)
async def get_function_graph(function_id: str, depth: int = 1):
    """Get a subgraph centered on a specific function."""
    try:
        db = get_db()

        # Get function and its neighbors
        query = f"""
        MATCH path = (f:Function {{id: $function_id}})-[*0..{depth}]-(connected)
        WITH collect(DISTINCT f) + collect(DISTINCT connected) as all_nodes
        UNWIND all_nodes as n
        RETURN DISTINCT n
        """
        node_results = db.execute_query(query, {"function_id": function_id})

        nodes = [
            NodeResponse(
                id=r['n']['id'],
                labels=['Function'],  # Simplified
                properties=dict(r['n'])
            )
            for r in node_results
        ]

        # Get edges between these nodes
        node_ids = [n.id for n in nodes]
        edges_query = """
        MATCH (a)-[r]->(b)
        WHERE a.id IN $node_ids AND b.id IN $node_ids
        RETURN a.id as source, type(r) as type, b.id as target, properties(r) as props
        """
        edge_results = db.execute_query(edges_query, {"node_ids": node_ids})

        edges = [
            EdgeResponse(
                source=r['source'],
                target=r['target'],
                type=r['type'],
                properties=r['props']
            )
            for r in edge_results
        ]

        return GraphResponse(nodes=nodes, edges=edges)
    except Exception as e:
        logger.error(f"Error getting function graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Custom Query Endpoint

@app.post("/query", response_model=List[Dict[str, Any]])
async def execute_cypher_query(request: CypherQueryRequest):
    """Execute a custom Cypher query."""
    try:
        db = get_db()
        results = db.execute_query(request.query, request.parameters)
        return results
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload
    )
