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

================================================================================
RECOMMENDED LLM WORKFLOW:
================================================================================

1. INITIAL UNDERSTANDING
   index_codebase(path="/project", clear=true)
   → Index entire codebase once
   → Returns stats: X functions, Y classes, Z relationships

2. EXPLORATION (as needed)
   find_function(name="calculate_total")
   get_function_callers(function_id="...")
   analyze_impact(entity_id="...", change_type="modify")
   → Understand code before changing it

3. BEFORE EDITING
   prepare_for_editing(file_paths=["auth.py", "session.py"])
   → Creates baseline snapshot

4. EDIT CODE
   <Use your Edit/Write tools to modify files>
   → This server doesn't edit code, you do!

5. AFTER EDITING (ONE CALL!)
   validate_after_edit(file_paths=["auth.py", "session.py"])
   → Re-indexes files
   → Creates snapshot
   → Compares with baseline
   → Validates all 4 conservation laws
   → Returns violations with exact file:line:column

6. IF VIOLATIONS FOUND
   → Read violation messages
   → Fix the code
   → Call validate_after_edit() again
   → Repeat until valid

7. SUCCESS!
   → is_valid: true
   → No breaking changes
   → Safe to commit

================================================================================
KEY CONCEPTS:
================================================================================

- INDEXING: Parse Python code into graph (functions, classes, calls, etc.)
- SNAPSHOTS: Save graph state for before/after comparison
- VALIDATION: Check 4 laws (signature conservation, reference integrity, etc.)
- WORKFLOWS: Composite tools (validate_after_edit) replace 4-5 manual steps

Tools are organized into 5 categories:
1. Indexing (2 tools) - Build the graph
2. Querying (6 tools) - Explore the graph
3. Analysis (2 tools) - Understand impact
4. Snapshots (3 tools) - Track changes
5. Workflows (2 tools) - Automated multi-step operations

Total: 15 tools available
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
from codegraph.workflow import WorkflowOrchestrator

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
workflow_orchestrator = WorkflowOrchestrator(db)

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
            description="""Parse and index Python code into the graph database.

WHEN TO USE:
- First time: index entire project with clear=true
- After editing: re-index specific files with clear=false (automatically removes old nodes)
- To update: directory indexing recursively scans all .py files

SUPPORTS: Single files, directories (recursive), entire projects
AUTOMATIC: Skips .git, __pycache__, venv, node_modules

EXAMPLE: index_codebase(path="/app/myproject", clear=true) → indexes all Python files
EXAMPLE: index_codebase(path="/app/utils.py", clear=false) → updates just this file""",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to Python file or directory to index"
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "Clear entire database before indexing (default: false). Use true for initial indexing, false for updates.",
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
            description="""Analyze impact of changing/deleting an entity BEFORE making changes.

WHEN TO USE:
- BEFORE modifying a function signature
- BEFORE deleting a function/class
- BEFORE renaming something
- To understand dependencies and affected code

WHAT IT SHOWS:
- Direct callers (who calls this function)
- Indirect callers (transitive dependencies)
- Total affected entities
- Recommendation for safe changes

USE CASE: Changing a function signature
1. analyze_impact(entity_id="calculate_total", change_type="modify")
   → Shows: Called by checkout.py:45, cart.py:78, invoice.py:120
2. Now you know which files need updating
3. Edit the function signature
4. Update all call sites shown in impact analysis
5. validate_after_edit() to verify no breaks

CHANGE TYPES:
- "modify" - Changing signature/implementation (most common)
- "delete" - Removing the entity entirely
- "rename" - Renaming (same as modify for dependencies)

EXAMPLE:
analyze_impact(entity_id="abc123", change_type="modify")
→ "Function calculate_total is called by 3 functions. Changing signature will affect checkout, cart, invoice.""",
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
            description="""Validate entire codebase against 4 conservation laws.

THE 4 LAWS:
1. Signature Conservation - Function calls must match signatures (handles default params)
2. Reference Integrity - All called functions must exist
3. Data Flow Consistency - Types should be compatible (warnings)
4. Structural Integrity - Graph structure is valid (no orphans)

WHEN TO USE:
- After editing code (but prefer validate_after_edit for full workflow)
- To check current state of codebase
- To find all violations at once

RETURNS:
- List of violations with severity (error/warning)
- Exact locations: file_path:line_number:column_number
- Detailed messages explaining the issue
- Suggested fixes for common problems
- Code snippets showing context

NOTE: validate_after_edit is preferred because it also:
- Re-indexes files first
- Creates snapshots
- Shows what changed
This tool only validates the current graph state.

EXAMPLE VIOLATIONS:
- "Function calculate_total expects 2 arguments but called with 1" (error)
- "Parameter 'amount' missing type annotation" (warning)
- "Orphaned function node: old_function" (warning)""",
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
        ),

        # Workflow orchestration tools
        Tool(
            name="validate_after_edit",
            description="""🔥 RECOMMENDED WORKFLOW TOOL 🔥
Complete workflow after editing files - replaces 4-5 manual tool calls with ONE.

WHAT IT DOES (automatically):
1. Re-indexes modified files (removes old nodes, adds new ones)
2. Creates new snapshot of graph state
3. Compares with previous snapshot (shows what changed)
4. Validates against all 4 conservation laws
5. Returns comprehensive report with violations

WHEN TO USE:
- After editing code files (use your Edit/Write tools first)
- To see full impact of changes in one call
- To validate code correctness automatically
- To detect breaking changes (signature mismatches, etc.)

RETURNS:
- entities_indexed, relationships_indexed
- changes_detected (nodes/edges added/removed/modified)
- violations with exact file:line:column locations
- is_valid (true/false), errors, warnings
- comprehensive message

WORKFLOW:
1. prepare_for_editing([files]) → creates baseline
2. <You edit files using Edit/Write tools>
3. validate_after_edit([files]) → validates everything!
4. If violations found → fix and repeat step 3
5. If valid → done!

EXAMPLE: After adding a parameter to calculate_total()
validate_after_edit(file_paths=["/app/utils.py"], description="Added tax parameter")
→ Shows: 1 parameter added, 3 call sites need updating, exact locations provided""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths that were edited"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of the changes made (optional)",
                        "default": ""
                    },
                    "create_snapshot": {
                        "type": "boolean",
                        "description": "Whether to create a snapshot (default: true)",
                        "default": True
                    },
                    "compare_with_previous": {
                        "type": "boolean",
                        "description": "Whether to compare with previous snapshot (default: true)",
                        "default": True
                    }
                },
                "required": ["file_paths"]
            }
        ),

        Tool(
            name="prepare_for_editing",
            description="""Prepare before editing files - creates baseline snapshot for later comparison.

WHEN TO USE:
- BEFORE you edit files (first step in edit workflow)
- To create a checkpoint of current state
- So validate_after_edit can compare before/after

WHAT IT DOES:
- Creates snapshot of current graph state
- Records which files you plan to edit
- Returns snapshot_id for reference

TYPICAL WORKFLOW:
1. prepare_for_editing([files_to_edit]) → creates baseline
2. <You edit files using your Edit/Write tools>
3. validate_after_edit([files_edited]) → compares with baseline automatically

NOTE: validate_after_edit automatically finds the most recent snapshot to compare with,
so you don't need to pass the snapshot_id. Just call prepare, edit, then validate!

EXAMPLE:
prepare_for_editing(file_paths=["/app/auth.py"], description="Adding OAuth support")
→ Creates baseline snapshot before you make changes""",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files that will be edited"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description of planned changes (optional)",
                        "default": ""
                    }
                },
                "required": ["file_paths"]
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
        elif name == "validate_after_edit":
            return await validate_after_edit_tool(arguments)
        elif name == "prepare_for_editing":
            return await prepare_for_editing_tool(arguments)
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
    elif os.path.isfile(path):
        # Delete old nodes from this specific file to prevent duplicates
        db.delete_nodes_from_file(path)
        logger.info(f"Deleted existing nodes from {path}")

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
                "snapshot_id": s.snapshot_id,
                "description": s.description,
                "timestamp": str(s.timestamp),
                "node_count": s.node_count,
                "edge_count": s.edge_count
            }
            for s in snapshots
        ],
        "count": len(snapshots)
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def validate_after_edit_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Complete workflow after editing files.

    Combines: re-index, snapshot, compare, validate.
    """
    file_paths = arguments["file_paths"]
    description = arguments.get("description", "")
    create_snapshot = arguments.get("create_snapshot", True)
    compare_with_previous = arguments.get("compare_with_previous", True)

    # Execute workflow
    result = workflow_orchestrator.validate_after_edit(
        file_paths=file_paths,
        description=description,
        create_snapshot=create_snapshot,
        compare_with_previous=compare_with_previous
    )

    # Convert to dict
    result_dict = result.to_dict()

    return [TextContent(type="text", text=json.dumps(result_dict, indent=2))]


async def prepare_for_editing_tool(arguments: Dict[str, Any]) -> list[TextContent]:
    """
    Prepare before editing files.

    Creates baseline snapshot.
    """
    file_paths = arguments["file_paths"]
    description = arguments.get("description", "")

    # Execute workflow
    result = workflow_orchestrator.prepare_for_editing(
        file_paths=file_paths,
        description=description
    )

    # Convert to dict
    result_dict = result.to_dict()

    return [TextContent(type="text", text=json.dumps(result_dict, indent=2))]
