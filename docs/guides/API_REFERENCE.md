# CodeGraph REST API Reference

## Overview

The CodeGraph REST API provides comprehensive endpoints for analyzing codebases through a graph database. All endpoints are read-only for code analysis - use your LLM's file editing tools to modify code.

**Base URL:** `http://localhost:8000`

**API Version:** 0.2.0

**Interactive Documentation:** Visit `http://localhost:8000/docs` (Swagger UI) or `http://localhost:8000/redoc` (ReDoc)

---

## Table of Contents

- [Authentication](#authentication)
- [Health & Info](#health--info)
- [Indexing](#indexing)
- [Graph Operations](#graph-operations)
- [Functions](#functions)
- [Validation](#validation)
- [Snapshots](#snapshots)
- [Git Integration](#git-integration)
- [Analysis](#analysis)
- [File Operations](#file-operations)
- [Real-Time Updates](#real-time-updates)
- [Error Handling](#error-handling)

---

## Authentication

Currently, the API does not require authentication. For production deployments, consider adding API keys or OAuth.

---

## Health & Info

### GET /

Root endpoint with API information.

**Response:**
```json
{
  "success": true,
  "message": "CodeGraph API - Read-Only Analysis Mode",
  "data": {
    "version": "0.2.0",
    "mode": "read-only",
    "description": "This API provides code analysis tools..."
  }
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "neo4j_uri": "bolt://localhost:7687"
}
```

**Status Codes:**
- `200`: Service healthy
- `503`: Service unavailable

### GET /stats

Get database statistics.

**Response:**
```json
{
  "stats": {
    "total_nodes": 144,
    "total_relationships": 215,
    "node_counts": {
      "Function": 42,
      "Class": 15,
      "Module": 8,
      "Parameter": 87,
      "Variable": 12,
      "CallSite": 28,
      "Type": 10,
      "Decorator": 5
    },
    "relationship_counts": {
      "DECLARES": 65,
      "HAS_PARAMETER": 87,
      "RESOLVES_TO": 28,
      "HAS_CALLSITE": 28,
      "INHERITS": 8,
      "RETURNS_TYPE": 27,
      "HAS_TYPE": 45
    }
  }
}
```

---

## Indexing

### POST /index

Parse and index Python code into the graph database.

**Request Body:**
```json
{
  "path": "/path/to/code",
  "clear": false
}
```

**Parameters:**
- `path` (string, required): Path to file or directory
- `clear` (boolean, optional): Clear database before indexing (default: false)

**Response:**
```json
{
  "success": true,
  "message": "Indexed 42 entities",
  "data": {
    "entities_indexed": 42,
    "relationships_created": 87,
    "time_elapsed": "3.2s",
    "files_processed": 8
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/user/project/src", "clear": false}'
```

**Status Codes:**
- `200`: Indexing successful
- `400`: Invalid path or parameters
- `500`: Indexing error

---

## Graph Operations

### GET /graph

Get graph data for visualization.

**Query Parameters:**
- `limit` (integer, optional): Maximum nodes to return (default: 100)
- `include_types` (string, optional): Comma-separated node types to include
- `exclude_types` (string, optional): Comma-separated node types to exclude

**Response:**
```json
{
  "nodes": [
    {
      "id": "func_abc123",
      "label": "calculate_total",
      "type": "Function",
      "properties": {
        "qualified_name": "myapp.billing.calculate_total",
        "signature": "calculate_total(items: list) -> float",
        "location": "myapp/billing.py:45:0"
      }
    }
  ],
  "edges": [
    {
      "id": "edge_123",
      "source": "func_xyz789",
      "target": "func_abc123",
      "type": "RESOLVES_TO",
      "properties": {
        "location": "myapp/orders.py:35:12",
        "arg_count": 1
      }
    }
  ],
  "metadata": {
    "total_nodes": 144,
    "total_edges": 215,
    "filtered_nodes": 100,
    "filtered_edges": 150
  }
}
```

**Example:**
```bash
# Get all nodes (limited to 100)
curl http://localhost:8000/graph

# Get specific types
curl "http://localhost:8000/graph?limit=50&include_types=Function,Class"

# Exclude certain types
curl "http://localhost:8000/graph?exclude_types=Parameter,Variable"
```

### GET /graph/subgraph/{entity_id}

Get subgraph centered on a specific entity.

**Path Parameters:**
- `entity_id` (string, required): Entity node ID

**Query Parameters:**
- `depth` (integer, optional): Relationship depth (default: 2)
- `direction` (string, optional): "in", "out", or "both" (default: "both")

**Response:**
```json
{
  "nodes": [...],
  "edges": [...],
  "center_node": {
    "id": "func_abc123",
    "type": "Function",
    "name": "calculate_total"
  },
  "depth": 2
}
```

**Example:**
```bash
curl "http://localhost:8000/graph/subgraph/func_abc123?depth=3&direction=out"
```

---

## Functions

### GET /functions

Search for functions.

**Query Parameters:**
- `name` (string, optional): Function name pattern
- `qualified_name` (string, optional): Full qualified name
- `limit` (integer, optional): Maximum results (default: 50)

**Response:**
```json
{
  "functions": [
    {
      "id": "func_abc123",
      "name": "calculate_total",
      "qualified_name": "myapp.billing.calculate_total",
      "signature": "calculate_total(items: list, discount: bool = False) -> float",
      "location": "myapp/billing.py:45:0",
      "visibility": "public",
      "docstring": "Calculate total with optional discount.",
      "parameters": [...]
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl "http://localhost:8000/functions?name=calculate*"
```

### GET /functions/{function_id}

Get detailed function information.

**Path Parameters:**
- `function_id` (string, required): Function node ID

**Response:**
```json
{
  "function": {
    "id": "func_abc123",
    "name": "calculate_total",
    "qualified_name": "myapp.billing.calculate_total",
    "signature": "calculate_total(items: list, discount: bool = False) -> float",
    "location": "myapp/billing.py:45:0",
    "visibility": "public",
    "is_async": false,
    "is_generator": false,
    "return_type": "float",
    "docstring": "Calculate total with optional discount.",
    "decorators": [],
    "parameters": [
      {
        "id": "param_1",
        "name": "items",
        "position": 0,
        "type_annotation": "list",
        "default_value": null,
        "kind": "positional"
      },
      {
        "id": "param_2",
        "name": "discount",
        "position": 1,
        "type_annotation": "bool",
        "default_value": "False",
        "kind": "positional"
      }
    ]
  }
}
```

**Example:**
```bash
curl http://localhost:8000/functions/func_abc123
```

### GET /functions/{function_id}/callers

Get all functions that call this function.

**Path Parameters:**
- `function_id` (string, required): Function node ID

**Response:**
```json
{
  "function_id": "func_abc123",
  "function_name": "calculate_total",
  "callers": [
    {
      "caller": {
        "id": "func_xyz789",
        "name": "process_order",
        "qualified_name": "myapp.orders.process_order",
        "location": "myapp/orders.py:23:0"
      },
      "call_site": {
        "id": "call_456",
        "location": "myapp/orders.py:35:12",
        "arg_count": 2,
        "lineno": 35,
        "col_offset": 12
      }
    }
  ],
  "total_callers": 1
}
```

**Example:**
```bash
curl http://localhost:8000/functions/func_abc123/callers
```

### GET /functions/{function_id}/callees

Get all functions that this function calls.

**Path Parameters:**
- `function_id` (string, required): Function node ID

**Response:**
```json
{
  "function_id": "func_xyz789",
  "function_name": "process_order",
  "callees": [
    {
      "callee": {
        "id": "func_abc123",
        "name": "calculate_total",
        "qualified_name": "myapp.billing.calculate_total",
        "location": "myapp/billing.py:45:0"
      },
      "call_site": {
        "id": "call_456",
        "location": "myapp/orders.py:35:12",
        "arg_count": 2
      }
    }
  ],
  "total_callees": 1
}
```

### GET /functions/{function_id}/dependencies

Get full dependency tree (recursive).

**Path Parameters:**
- `function_id` (string, required): Function node ID

**Query Parameters:**
- `depth` (integer, optional): Maximum depth (default: 2)

**Response:**
```json
{
  "function_id": "func_xyz789",
  "function_name": "process_order",
  "dependencies": {
    "direct": [...],
    "indirect": [...],
    "depth_reached": 2
  },
  "total_dependencies": 5
}
```

---

## Validation

### GET /validate

Validate codebase against 4 conservation laws.

**Query Parameters:**
- `include_pyright` (boolean, optional): Run pyright type checker (default: false)
- `changed_only` (boolean, optional): Only validate changed nodes (default: false)

**Response:**
```json
{
  "valid": false,
  "violations": [
    {
      "law": "Signature Conservation",
      "type": "signature_mismatch",
      "severity": "error",
      "entity_id": "call_456",
      "message": "Function calculate_total expects 2 arguments but called with 1",
      "file_path": "myapp/orders.py",
      "line_number": 35,
      "column_number": 12,
      "code_snippet": "    total = calculate_total(items)\n            ^^^^^^^^^^^^^^^^^^^^^^^^^^^",
      "suggested_fix": "Add missing argument: calculate_total(items, False)",
      "details": {
        "expected_args": 2,
        "actual_args": 1,
        "function_signature": "calculate_total(items: list, discount: bool = False) -> float"
      }
    }
  ],
  "summary": {
    "signature_conservation": 1,
    "reference_integrity": 0,
    "data_flow_consistency": 0,
    "structural_integrity": 0
  },
  "total_violations": 1,
  "timestamp": "2025-01-19T15:30:00Z"
}
```

**Conservation Laws:**
1. **Signature Conservation**: Function signatures match call sites
2. **Reference Integrity**: All references resolve to valid entities
3. **Data Flow Consistency**: Type annotations are consistent
4. **Structural Integrity**: Graph structure is valid

**Example:**
```bash
# Quick validation
curl http://localhost:8000/validate

# With pyright type checking
curl "http://localhost:8000/validate?include_pyright=true"

# Only changed nodes
curl "http://localhost:8000/validate?changed_only=true"
```

---

## Snapshots

### POST /snapshot/create

Create a snapshot of current graph state.

**Query Parameters:**
- `description` (string, optional): Snapshot description
- `tags` (string, optional): Comma-separated tags

**Response:**
```json
{
  "snapshot_id": "snap_20250119_143022",
  "description": "Before refactoring",
  "timestamp": "2025-01-19T14:30:22Z",
  "tags": ["refactoring", "billing"],
  "stats": {
    "total_nodes": 144,
    "total_edges": 215
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Before%20refactoring&tags=refactoring,billing"
```

### GET /snapshot/list

List all snapshots.

**Query Parameters:**
- `limit` (integer, optional): Maximum snapshots to return (default: 20)

**Response:**
```json
{
  "snapshots": [
    {
      "snapshot_id": "snap_20250119_143022",
      "description": "Before refactoring",
      "timestamp": "2025-01-19T14:30:22Z",
      "tags": ["refactoring", "billing"]
    }
  ],
  "total": 1
}
```

### POST /snapshot/compare

Compare two snapshots.

**Query Parameters:**
- `old_snapshot_id` (string, required): Earlier snapshot
- `new_snapshot_id` (string, required): Later snapshot

**Response:**
```json
{
  "comparison": {
    "nodes_added": [
      {
        "id": "func_new123",
        "type": "Function",
        "name": "new_helper",
        "location": "myapp/helpers.py:10:0"
      }
    ],
    "nodes_removed": [],
    "nodes_modified": [
      {
        "id": "func_abc123",
        "type": "Function",
        "name": "calculate_total",
        "changes": {
          "signature": {
            "old": "calculate_total(items: list) -> float",
            "new": "calculate_total(items: list, discount: bool = False) -> float"
          },
          "parameters": {
            "added": ["discount"]
          }
        }
      }
    ],
    "edges_added": 3,
    "edges_removed": 0,
    "edges_modified": []
  },
  "summary": {
    "total_changes": 4,
    "nodes_changed": 1,
    "edges_changed": 3
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/snapshot/compare?old_snapshot_id=snap_123&new_snapshot_id=snap_456"
```

---

## Git Integration

### GET /commits

List git commits.

**Query Parameters:**
- `limit` (integer, optional): Maximum commits (default: 20)
- `since` (string, optional): ISO timestamp for commits after this date

**Response:**
```json
{
  "commits": [
    {
      "hash": "8a523e6",
      "message": "Add discount parameter to calculate_total",
      "author": "John Doe",
      "timestamp": "2025-01-19T14:30:00Z",
      "indexed": true
    }
  ],
  "total": 1,
  "repository_path": "/home/user/project"
}
```

### POST /commits/{commit_hash}/index

Index code at a specific commit.

**Path Parameters:**
- `commit_hash` (string, required): Git commit hash

**Response:**
```json
{
  "success": true,
  "message": "Indexed commit 8a523e6",
  "data": {
    "commit_hash": "8a523e6",
    "entities_indexed": 42,
    "snapshot_id": "snap_8a523e6"
  }
}
```

### GET /commits/diff/files

List files changed between commits.

**Query Parameters:**
- `old` (string, required): Old commit hash
- `new` (string, required): New commit hash

**Response:**
```json
{
  "files": [
    {
      "path": "myapp/billing.py",
      "status": "modified",
      "additions": 5,
      "deletions": 2,
      "is_binary": false
    }
  ],
  "total_files": 1
}
```

### GET /commits/diff/file

Get text diff for a specific file.

**Query Parameters:**
- `old` (string, required): Old commit hash
- `new` (string, required): New commit hash
- `filepath` (string, required): File path

**Response:**
```json
{
  "filepath": "myapp/billing.py",
  "diff": "@@ -45,7 +45,10 @@\n-def calculate_total(items: list) -> float:\n+def calculate_total(items: list, discount: bool = False) -> float:\n     total = sum(item.price for item in items)\n+    if discount:\n+        total *= 0.9\n     return total",
  "additions": 3,
  "deletions": 1,
  "is_binary": false
}
```

---

## Analysis

### POST /impact

Analyze impact of modifying or deleting an entity.

**Request Body:**
```json
{
  "entity_id": "func_abc123",
  "change_type": "delete"
}
```

**Parameters:**
- `entity_id` (string, required): Entity node ID
- `change_type` (string, required): "modify" or "delete"

**Response:**
```json
{
  "entity_id": "func_abc123",
  "entity_name": "calculate_total",
  "change_type": "delete",
  "impact": {
    "affected_callers": [
      {
        "id": "func_xyz789",
        "name": "process_order",
        "location": "myapp/orders.py:23:0",
        "reason": "Calls this function at line 35"
      }
    ],
    "affected_references": [],
    "affected_subclasses": [],
    "severity": "high",
    "recommendation": "Update 1 caller before deletion"
  },
  "total_affected": 1
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/impact \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "func_abc123", "change_type": "delete"}'
```

### POST /search

Search for entities by pattern.

**Request Body:**
```json
{
  "pattern": "calculate*",
  "entity_type": "Function"
}
```

**Parameters:**
- `pattern` (string, required): Search pattern (supports wildcards)
- `entity_type` (string, optional): Filter by type (Function, Class, Variable, Module)

**Response:**
```json
{
  "results": [
    {
      "id": "func_abc123",
      "type": "Function",
      "name": "calculate_total",
      "qualified_name": "myapp.billing.calculate_total",
      "location": "myapp/billing.py:45:0"
    },
    {
      "id": "func_def456",
      "type": "Function",
      "name": "calculate_tax",
      "qualified_name": "myapp.billing.calculate_tax",
      "location": "myapp/billing.py:78:0"
    }
  ],
  "total_results": 2
}
```

---

## File Operations

### GET /files

List all indexed files.

**Response:**
```json
{
  "files": [
    {
      "path": "myapp/billing.py",
      "module_id": "mod_abc123",
      "functions": 5,
      "classes": 2,
      "last_indexed": "2025-01-19T14:30:00Z"
    }
  ],
  "total": 1
}
```

### POST /mark-changed

Mark specific files as changed for incremental validation.

**Request Body:**
```json
{
  "files": ["myapp/billing.py", "myapp/orders.py"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Marked 2 files as changed",
  "data": {
    "files_marked": 2,
    "nodes_marked": 15
  }
}
```

---

## Real-Time Updates

### WebSocket /ws

Subscribe to real-time graph updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Graph updated:', update);
};
```

**Message Format:**
```json
{
  "type": "graph_update",
  "timestamp": "2025-01-19T15:30:00Z",
  "changes": {
    "nodes_added": [...],
    "nodes_modified": [...],
    "edges_added": [...]
  }
}
```

### POST /watch/start

Start watching a directory for file changes.

**Request Body:**
```json
{
  "path": "/home/user/project/myapp"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Started watching /home/user/project/myapp",
  "data": {
    "watching": true,
    "path": "/home/user/project/myapp"
  }
}
```

### POST /watch/stop

Stop file watching.

**Response:**
```json
{
  "success": true,
  "message": "Stopped file watching"
}
```

### GET /watch/status

Get file watching status.

**Response:**
```json
{
  "watching": true,
  "path": "/home/user/project/myapp",
  "last_event": "2025-01-19T15:30:00Z"
}
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "error": {
    "code": "ENTITY_NOT_FOUND",
    "message": "Function with ID 'func_xyz' does not exist",
    "details": {
      "entity_id": "func_xyz",
      "entity_type": "Function"
    }
  }
}
```

### HTTP Status Codes

- `200`: Success
- `201`: Created
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (entity doesn't exist)
- `422`: Unprocessable Entity (validation error)
- `500`: Internal Server Error
- `503`: Service Unavailable (database connection issue)

### Common Error Codes

| Code | Description |
|------|-------------|
| `ENTITY_NOT_FOUND` | Requested entity doesn't exist |
| `INVALID_PARAMETER` | Invalid query parameter or request body |
| `DATABASE_ERROR` | Neo4j database error |
| `PARSING_ERROR` | Python code parsing failed |
| `SNAPSHOT_NOT_FOUND` | Snapshot doesn't exist |
| `VALIDATION_FAILED` | Conservation law violations found |
| `FILE_NOT_FOUND` | File path doesn't exist |
| `GIT_ERROR` | Git operation failed |

---

## Rate Limiting

Currently no rate limiting is enforced. For production deployments, consider adding rate limiting middleware.

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters:**
- `limit` (integer): Maximum items per page (default varies by endpoint)
- `offset` (integer): Number of items to skip (default: 0)

**Example:**
```bash
curl "http://localhost:8000/functions?limit=10&offset=20"
```

---

## Filtering

Many endpoints support filtering by type:

**Query Parameters:**
- `include_types`: Comma-separated types to include
- `exclude_types`: Comma-separated types to exclude

**Example:**
```bash
curl "http://localhost:8000/graph?include_types=Function,Class"
```

---

## CORS

The API supports CORS. Configure allowed origins in `.env`:

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

---

## OpenAPI Specification

Download the OpenAPI specification:

```bash
curl http://localhost:8000/openapi.json > codegraph-api.json
```

---

## SDK Examples

### Python Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Index codebase
response = requests.post(f"{BASE_URL}/index", json={
    "path": "/home/user/project",
    "clear": False
})
print(response.json())

# Validate
response = requests.get(f"{BASE_URL}/validate")
report = response.json()
print(f"Total violations: {report['total_violations']}")

# Create snapshot
response = requests.post(
    f"{BASE_URL}/snapshot/create",
    params={"description": "Before refactoring"}
)
snapshot = response.json()
print(f"Created snapshot: {snapshot['snapshot_id']}")
```

### JavaScript Client

```javascript
const BASE_URL = 'http://localhost:8000';

// Index codebase
const indexResponse = await fetch(`${BASE_URL}/index`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ path: '/home/user/project', clear: false })
});
const indexData = await indexResponse.json();

// Validate
const validateResponse = await fetch(`${BASE_URL}/validate`);
const report = await validateResponse.json();
console.log(`Total violations: ${report.total_violations}`);

// Get graph
const graphResponse = await fetch(`${BASE_URL}/graph?limit=100`);
const graph = await graphResponse.json();
console.log(`Nodes: ${graph.nodes.length}, Edges: ${graph.edges.length}`);
```

---

## Best Practices

### 1. Incremental Indexing

Don't clear the database unnecessarily:

```bash
# Good: Incremental update
curl -X POST http://localhost:8000/index -d '{"path": "myapp/file.py", "clear": false}'

# Avoid: Full rebuild (slow)
curl -X POST http://localhost:8000/index -d '{"path": ".", "clear": true}'
```

### 2. Use Changed-Only Validation

After editing specific files:

```bash
# Mark files as changed
curl -X POST http://localhost:8000/mark-changed -d '{"files": ["myapp/billing.py"]}'

# Validate only changed nodes
curl "http://localhost:8000/validate?changed_only=true"
```

### 3. Create Snapshots Before Major Changes

```bash
# Before
curl -X POST "http://localhost:8000/snapshot/create?description=Before%20refactoring"

# Make changes, re-index

# After
curl -X POST "http://localhost:8000/snapshot/create?description=After%20refactoring"

# Compare
curl -X POST "http://localhost:8000/snapshot/compare?old_snapshot_id=snap1&new_snapshot_id=snap2"
```

### 4. Use Impact Analysis

Before deleting or modifying shared functions:

```bash
curl -X POST http://localhost:8000/impact \
  -d '{"entity_id": "func_abc123", "change_type": "delete"}'
```

---

## Troubleshooting

### Connection Refused

**Issue:** Cannot connect to API

**Solution:**
1. Check if backend is running: `curl http://localhost:8000/health`
2. Verify port 8000 is not in use: `lsof -i :8000`
3. Check backend logs for errors

### Database Connection Error

**Issue:** `database_connected: false` in health check

**Solution:**
1. Ensure Neo4j is running: `docker ps | grep neo4j`
2. Test Neo4j connection: `curl http://localhost:7474`
3. Verify credentials in `.env`

### Parsing Errors

**Issue:** Indexing fails with parsing errors

**Solution:**
1. Ensure Python files are syntactically valid
2. Check file encoding (must be UTF-8)
3. Review error details in response
4. Try indexing files individually to isolate issue

---

## Support

- API Documentation: http://localhost:8000/docs
- GitHub Issues: [repository/issues]
- Developer Guide: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- MCP Server: [MCP_SERVER.md](../architecture/MCP_SERVER.md)

---

**Last Updated:** 2025-01-19
**API Version:** 0.2.0
