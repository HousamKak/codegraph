#!/usr/bin/env python3
"""
MCP Server for CodeGraph - Read-Only Code Analysis Tool

This server provides LLMs with "eyes" to see code relationships through a graph database.
The LLM uses its own file editing tools to modify code, and uses this server to:
  - Understand code structure
  - Find function dependencies
  - Analyze impact of potential changes
  - Validate code against conservation laws

NO EDITING is done by this server - it's purely for analysis.
"""

import asyncio
import os
import sys
import logging
import json
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from codegraph.db import CodeGraphDB
from codegraph.parser import PythonParser
from codegraph.builder import GraphBuilder
from codegraph.query import QueryInterface
from codegraph.validators import ConservationValidator
from codegraph.snapshot import SnapshotManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get Neo4j connection from environment
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Initialize components
db = CodeGraphDB(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
query_interface = QueryInterface(db)
validator = ConservationValidator(db)
snapshot_manager = SnapshotManager(db)
parser = PythonParser()
builder = GraphBuilder(db)

# Create MCP server
app = Server("codegraph")

logger.info(f"CodeGraph MCP Server initialized (read-only analysis mode)")
logger.info(f"Connected to Neo4j at {NEO4J_URI}")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available read-only analysis tools."""
    return [
        # Indexing
        Tool(
            name="index_codebase",
            description="Parse and index Python code into the graph database. Call this after you've edited files to update the graph. Supports both files and directories.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to Python file or directory to index"
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "Clear database before indexing (default: false)",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        ),

        # Querying
        Tool(
            name="find_function",
            description="Find functions by name or qualified name. Returns function details including signature, location, and parameters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Simple function name (e.g., 'calculate_total')"
                    },
                    "qualified_name": {
                        "type": "string",
                        "description": "Fully qualified name (e.g., 'myapp.utils.calculate_total')"
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="get_function_details",
            description="Get complete details about a function including its signature and all parameters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "Function ID (from find_function result)"
                    }
                },
                "required": ["function_id"]
            }
        ),

        Tool(
            name="get_function_callers",
            description="Find all functions that call a given function. Essential for understanding impact of signature changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "Function ID to find callers for"
                    }
                },
                "required": ["function_id"]
            }
        ),

        Tool(
            name="get_function_callees",
            description="Find all functions called by a given function. Shows the function's dependencies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "Function ID to find callees for"
                    }
                },
                "required": ["function_id"]
            }
        ),

        Tool(
            name="get_function_dependencies",
            description="Get complete dependency graph for a function (both callers and callees) up to a specified depth.",
            inputSchema={
                "type": "object",
                "properties": {
                    "function_id": {
                        "type": "string",
                        "description": "Function ID"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Traversal depth (default: 1)",
                        "default": 1
                    }
                },
                "required": ["function_id"]
            }
        ),

        # Analysis
        Tool(
            name="analyze_impact",
            description="Analyze the impact of changing or deleting an entity. Shows all affected code before you make changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID (function, class, etc.)"
                    },
                    "change_type": {
                        "type": "string",
                        "description": "Type of change: 'modify', 'delete', or 'rename'",
                        "enum": ["modify", "delete", "rename"],
                        "default": "modify"
                    }
                },
                "required": ["entity_id"]
            }
        ),

        Tool(
            name="search_code",
            description="Search for entities by name pattern (regex). Useful for finding similar functions or classes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for"
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Filter by entity type: Function, Class, Variable, Parameter",
                        "enum": ["Function", "Class", "Variable", "Parameter"]
                    }
                },
                "required": ["pattern"]
            }
        ),

        # Validation
        Tool(
            name="validate_codebase",
            description="Check all 4 conservation laws and return violations. Call this after editing code to see what broke. Returns detailed violation information with file paths and line numbers.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        Tool(
            name="get_graph_stats",
            description="Get statistics about the indexed codebase (number of functions, classes, relationships, etc.)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        # Snapshot tools
        Tool(
            name="create_snapshot",
            description="Create a snapshot of the current graph state. Call this BEFORE editing code to save the current state for later comparison.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Description of this snapshot (e.g., 'Before adding max_value parameter')",
                        "default": ""
                    }
                },
                "required": []
            }
        ),

        Tool(
            name="compare_snapshots",
            description="Compare two snapshots to detect changes in the graph. Returns detailed diff showing nodes and edges that were added, removed, or modified. Use this AFTER editing and re-indexing to see what changed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_snapshot_id": {
                        "type": "string",
                        "description": "ID of the first (earlier) snapshot"
                    },
                    "new_snapshot_id": {
                        "type": "string",
                        "description": "ID of the second (later) snapshot"
                    }
                },
                "required": ["old_snapshot_id", "new_snapshot_id"]
            }
        ),

        Tool(
            name="list_snapshots",
            description="List all available snapshots with their IDs and metadata.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "index_codebase":
            return await index_codebase(arguments)
        elif name == "find_function":
            return await find_function(arguments)
        elif name == "get_function_details":
            return await get_function_details(arguments)
        elif name == "get_function_callers":
            return await get_function_callers(arguments)
        elif name == "get_function_callees":
            return await get_function_callees(arguments)
        elif name == "get_function_dependencies":
            return await get_function_dependencies(arguments)
        elif name == "analyze_impact":
            return await analyze_impact(arguments)
        elif name == "search_code":
            return await search_code(arguments)
        elif name == "validate_codebase":
            return await validate_codebase(arguments)
        elif name == "get_graph_stats":
            return await get_graph_stats(arguments)
        elif name == "create_snapshot":
            return await create_snapshot(arguments)
        elif name == "compare_snapshots":
            return await compare_snapshots_tool(arguments)
        elif name == "list_snapshots":
            return await list_snapshots_tool(arguments)
        else:
            return [TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
    except Exception as e:
        logger.error(f"Error executing {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


# Tool implementations

async def index_codebase(arguments: Dict[str, Any]) -> list[TextContent]:
    """Index a codebase into the graph."""
    path = arguments["path"]
    clear = arguments.get("clear", False)

    if clear:
        db.clear_database()
        logger.info("Database cleared")

    db.initialize_schema()

    # Parse code
    if os.path.isfile(path):
        entities, relationships = parser.parse_file(path)
    elif os.path.isdir(path):
        entities, relationships = parser.parse_directory(path)
    else:
        return [TextContent(
            type="text",
            text=f"Error: Path not found: {path}"
        )]

    # Build graph
    builder.build_graph(entities, relationships)

    # Get stats
    stats = db.get_statistics()

    result = {
        "success": True,
        "path": path,
        "entities_indexed": len(entities),
        "relationships_created": len(relationships),
        "statistics": stats
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def find_function(arguments: Dict[str, Any]) -> list[TextContent]:
    """Find functions by name."""
    name = arguments.get("name")
    qualified_name = arguments.get("qualified_name")

    results = query_interface.find_function(name=name, qualified_name=qualified_name)

    return [TextContent(
        type="text",
        text=json.dumps({"functions": results}, indent=2)
    )]


async def get_function_details(arguments: Dict[str, Any]) -> list[TextContent]:
    """Get function signature details."""
    function_id = arguments["function_id"]

    result = query_interface.get_function_signature(function_id)

    if not result:
        return [TextContent(
            type="text",
            text=f"Function not found: {function_id}"
        )]

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_function_callers(arguments: Dict[str, Any]) -> list[TextContent]:
    """Find all callers of a function."""
    function_id = arguments["function_id"]

    callers = query_interface.find_callers(function_id)

    return [TextContent(
        type="text",
        text=json.dumps({"callers": callers, "count": len(callers)}, indent=2)
    )]


async def get_function_callees(arguments: Dict[str, Any]) -> list[TextContent]:
    """Find all functions called by a function."""
    function_id = arguments["function_id"]

    callees = query_interface.find_callees(function_id)

    return [TextContent(
        type="text",
        text=json.dumps({"callees": callees, "count": len(callees)}, indent=2)
    )]


async def get_function_dependencies(arguments: Dict[str, Any]) -> list[TextContent]:
    """Get complete dependency graph."""
    function_id = arguments["function_id"]
    depth = arguments.get("depth", 1)

    deps = query_interface.get_function_dependencies(function_id, depth)

    return [TextContent(type="text", text=json.dumps(deps, indent=2))]


async def analyze_impact(arguments: Dict[str, Any]) -> list[TextContent]:
    """Analyze impact of changing an entity."""
    entity_id = arguments["entity_id"]
    change_type = arguments.get("change_type", "modify")

    impact = query_interface.get_impact_analysis(entity_id, change_type)

    return [TextContent(type="text", text=json.dumps(impact, indent=2))]


async def search_code(arguments: Dict[str, Any]) -> list[TextContent]:
    """Search for entities by pattern."""
    pattern = arguments["pattern"]
    entity_type = arguments.get("entity_type")

    results = query_interface.search_by_pattern(pattern, entity_type)

    return [TextContent(
        type="text",
        text=json.dumps({"results": results, "count": len(results)}, indent=2)
    )]


async def validate_codebase(arguments: Dict[str, Any]) -> list[TextContent]:
    """Validate conservation laws."""
    violations = validator.validate_all()

    # Group violations by severity
    errors = [v for v in violations if v.severity == "error"]
    warnings = [v for v in violations if v.severity == "warning"]

    # Convert to dict for JSON serialization
    violations_dict = [
        {
            "violation_type": v.violation_type.value,
            "severity": v.severity,
            "entity_id": v.entity_id,
            "message": v.message,
            "details": v.details,
            "suggested_fix": v.suggested_fix,
            "file_path": v.file_path,
            "line_number": v.line_number,
            "column_number": v.column_number,
            "code_snippet": v.code_snippet,
            "old_value": v.old_value,
            "new_value": v.new_value
        }
        for v in violations
    ]

    result = {
        "total_violations": len(violations),
        "errors": len(errors),
        "warnings": len(warnings),
        "safe_to_commit": len(errors) == 0,
        "violations": violations_dict
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_graph_stats(arguments: Dict[str, Any]) -> list[TextContent]:
    """Get graph statistics."""
    stats = db.get_statistics()

    return [TextContent(type="text", text=json.dumps(stats, indent=2))]


async def main():
    """Run the MCP server."""
    logger.info("Starting CodeGraph MCP Server (read-only analysis mode)")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())


# Snapshot tool implementations

async def create_snapshot(arguments: Dict[str, Any]) -> list[TextContent]:
    """Create a snapshot of the current graph state."""
    description = arguments.get("description", "")
    
    snapshot_id = snapshot_manager.create_snapshot(description)
    snapshot = snapshot_manager.get_snapshot_data(snapshot_id)
    
    result = {
        "snapshot_id": snapshot_id,
        "description": description,
        "timestamp": snapshot["timestamp"],
        "node_count": snapshot["node_count"],
        "edge_count": snapshot["edge_count"]
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def compare_snapshots_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """Compare two snapshots."""
    old_id = arguments["old_snapshot_id"]
    new_id = arguments["new_snapshot_id"]
    
    diff = snapshot_manager.compare_snapshots(old_id, new_id)
    
    result = {
        "old_snapshot_id": old_id,
        "new_snapshot_id": new_id,
        "summary": {
            "nodes_added": len(diff.nodes.added),
            "nodes_removed": len(diff.nodes.removed),
            "nodes_modified": len(diff.nodes.modified),
            "edges_added": len(diff.edges.added),
            "edges_removed": len(diff.edges.removed),
            "edges_modified": len(diff.edges.modified)
        },
        "nodes": {
            "added": [{"id": n.get("id"), "labels": n.get("labels"), "name": n.get("name")} for n in diff.nodes.added],
            "removed": [{"id": n.get("id"), "labels": n.get("labels"), "name": n.get("name")} for n in diff.nodes.removed],
            "modified": [{"id": n.get("id"), "labels": n.get("labels"), "name": n.get("name")} for n in diff.nodes.modified]
        },
        "edges": {
            "added": diff.edges.added[:20],  # Limit for readability
            "removed": diff.edges.removed[:20],
            "modified": diff.edges.modified[:20]
        }
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def list_snapshots_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """List all snapshots."""
    snapshots = snapshot_manager.list_snapshots()
    
    result = {
        "snapshots": [
            {
                "snapshot_id": s["snapshot_id"],
                "description": s.get("description", ""),
                "timestamp": s["timestamp"],
                "node_count": s["node_count"],
                "edge_count": s["edge_count"]
            }
            for s in snapshots
        ],
        "count": len(snapshots)
    }
    
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
