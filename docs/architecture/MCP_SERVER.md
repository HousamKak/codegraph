# CodeGraph MCP Server

## Overview

The CodeGraph MCP (Model Context Protocol) Server provides 13 read-only analysis tools that enable Large Language Models to understand code structure through graph queries. The LLM uses its standard file editing tools for code changes, while CodeGraph provides semantic insights and validation.

**Key Principle:** LLM does ALL editing. CodeGraph provides analysis.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                 LLM (Claude, GPT-4)                  │
│              Uses: Edit, Write, Read                 │
└──────────────────┬──────────────────────────────────┘
                   │ MCP Protocol
                   ▼
┌─────────────────────────────────────────────────────┐
│              MCP Server (13 Tools)                   │
│           backend/codegraph/mcp_server.py            │
└──────────────────┬──────────────────────────────────┘
                   │ Neo4j Driver
                   ▼
┌─────────────────────────────────────────────────────┐
│                Neo4j Graph Database                  │
│        Nodes: Function, Class, Variable, etc.        │
│       Edges: DECLARES, CALLS, INHERITS, etc.         │
└─────────────────────────────────────────────────────┘
```

## Installation & Configuration

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Start Neo4j

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 3. Configure Environment

Create `.env` file in backend directory:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 4. Configure Claude Code

Add to your Claude Code MCP configuration:

```json
{
  "mcpServers": {
    "codegraph": {
      "command": "python",
      "args": ["/path/to/codegraph/backend/codegraph/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

### 5. Test Connection

```bash
# Run MCP server directly
cd backend/codegraph
python mcp_server.py
```

The server will start and wait for MCP protocol messages on stdin/stdout.

## The 13 MCP Tools

### Category 1: Indexing & Stats

#### 1. `index_codebase`

Parse and index Python code into the graph database.

**Parameters:**
- `path` (string, required): Path to file or directory
- `clear` (boolean, optional): Clear database before indexing (default: false)

**Example:**
```json
{
  "path": "/home/user/project/src",
  "clear": false
}
```

**Returns:**
```json
{
  "status": "success",
  "stats": {
    "functions": 42,
    "classes": 15,
    "variables": 87,
    "relationships": 215
  },
  "time_elapsed": "3.2s"
}
```

**Use Cases:**
- Initial indexing of codebase
- Re-indexing after LLM edits files
- Incremental updates (clear=false)

---

#### 2. `get_graph_stats`

Get database statistics and summary.

**Parameters:** None

**Example:**
```json
{}
```

**Returns:**
```json
{
  "total_nodes": 144,
  "total_relationships": 215,
  "node_counts": {
    "Function": 42,
    "Class": 15,
    "Parameter": 87,
    "CallSite": 28,
    "Module": 8,
    "Variable": 12,
    "Type": 10
  },
  "relationship_counts": {
    "DECLARES": 65,
    "HAS_PARAMETER": 87,
    "RESOLVES_TO": 28,
    "INHERITS": 8,
    "RETURNS_TYPE": 27
  }
}
```

**Use Cases:**
- Check indexing success
- Verify graph size
- Monitor growth over time

---

### Category 2: Querying

#### 3. `find_function`

Find functions by name or qualified name.

**Parameters:**
- `name` (string, optional): Simple function name
- `qualified_name` (string, optional): Full dotted path

At least one parameter required.

**Example:**
```json
{
  "name": "calculate_total"
}
```

**Returns:**
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
      "is_async": false,
      "return_type": "float"
    }
  ]
}
```

**Use Cases:**
- Locate function before editing
- Check if function exists
- Find multiple functions with same name

---

#### 4. `get_function_details`

Get complete information about a function.

**Parameters:**
- `function_id` (string, required): Function node ID

**Example:**
```json
{
  "function_id": "func_abc123"
}
```

**Returns:**
```json
{
  "function": {
    "id": "func_abc123",
    "name": "calculate_total",
    "qualified_name": "myapp.billing.calculate_total",
    "signature": "calculate_total(items: list, discount: bool = False) -> float",
    "location": "myapp/billing.py:45:0",
    "visibility": "public",
    "docstring": "Calculate total with optional discount.",
    "decorators": [],
    "parameters": [
      {
        "name": "items",
        "type_annotation": "list",
        "position": 0,
        "default_value": null,
        "kind": "positional"
      },
      {
        "name": "discount",
        "type_annotation": "bool",
        "position": 1,
        "default_value": "False",
        "kind": "positional"
      }
    ],
    "return_type": "float"
  }
}
```

**Use Cases:**
- Understand function signature before modification
- Check parameter types
- See docstring and decorators

---

#### 5. `get_function_callers`

Find all functions that call a specific function.

**Parameters:**
- `function_id` (string, required): Function node ID

**Example:**
```json
{
  "function_id": "func_abc123"
}
```

**Returns:**
```json
{
  "callers": [
    {
      "caller": {
        "id": "func_xyz789",
        "name": "process_order",
        "qualified_name": "myapp.orders.process_order",
        "location": "myapp/orders.py:23:0"
      },
      "call_site": {
        "location": "myapp/orders.py:35:12",
        "arg_count": 2
      }
    }
  ],
  "total_callers": 1
}
```

**Use Cases:**
- Impact analysis before changing function signature
- Find all usages of a function
- Validate that all callers will be updated

---

#### 6. `get_function_callees`

Find all functions that a specific function calls.

**Parameters:**
- `function_id` (string, required): Function node ID

**Example:**
```json
{
  "function_id": "func_xyz789"
}
```

**Returns:**
```json
{
  "callees": [
    {
      "callee": {
        "id": "func_abc123",
        "name": "calculate_total",
        "qualified_name": "myapp.billing.calculate_total",
        "location": "myapp/billing.py:45:0"
      },
      "call_site": {
        "location": "myapp/orders.py:35:12",
        "arg_count": 2
      }
    },
    {
      "callee": {
        "id": "func_def456",
        "name": "validate_items",
        "qualified_name": "myapp.validation.validate_items",
        "location": "myapp/validation.py:12:0"
      },
      "call_site": {
        "location": "myapp/orders.py:32:8",
        "arg_count": 1
      }
    }
  ],
  "total_callees": 2
}
```

**Use Cases:**
- Understand function dependencies
- Trace execution flow
- Identify dead code

---

#### 7. `get_function_dependencies`

Get full dependency tree for a function (recursive).

**Parameters:**
- `function_id` (string, required): Function node ID
- `depth` (integer, optional): Maximum depth (default: 2)

**Example:**
```json
{
  "function_id": "func_xyz789",
  "depth": 3
}
```

**Returns:**
```json
{
  "dependencies": {
    "direct": [...],
    "indirect": [...],
    "depth_reached": 3
  },
  "total_dependencies": 8
}
```

**Use Cases:**
- Full impact analysis
- Understanding code complexity
- Refactoring planning

---

#### 8. `search_code`

Search for entities by pattern.

**Parameters:**
- `pattern` (string, required): Search pattern (supports wildcards)
- `entity_type` (string, optional): Filter by type (Function, Class, Variable, Module)

**Example:**
```json
{
  "pattern": "calculate*",
  "entity_type": "Function"
}
```

**Returns:**
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
      "id": "func_ghi789",
      "type": "Function",
      "name": "calculate_tax",
      "qualified_name": "myapp.billing.calculate_tax",
      "location": "myapp/billing.py:78:0"
    }
  ],
  "total_results": 2
}
```

**Use Cases:**
- Explore codebase
- Find related functions
- Discover naming patterns

---

### Category 3: Analysis

#### 9. `analyze_impact`

Analyze what would break if an entity is modified or deleted.

**Parameters:**
- `entity_id` (string, required): Entity node ID
- `change_type` (string, required): "modify" or "delete"

**Example:**
```json
{
  "entity_id": "func_abc123",
  "change_type": "delete"
}
```

**Returns:**
```json
{
  "impact": {
    "affected_callers": [
      {
        "id": "func_xyz789",
        "name": "process_order",
        "location": "myapp/orders.py:23:0",
        "reason": "Calls this function at orders.py:35"
      }
    ],
    "affected_references": [],
    "affected_subclasses": [],
    "severity": "high",
    "recommendation": "Update 1 caller before deletion"
  }
}
```

**Use Cases:**
- Before deleting a function
- Before changing function signature
- Refactoring planning

---

#### 10. `validate_codebase`

Check all 4 conservation laws and report violations.

**Parameters:**
- `include_pyright` (boolean, optional): Run pyright type checker (default: false)

**Example:**
```json
{
  "include_pyright": true
}
```

**Returns:**
```json
{
  "valid": false,
  "violations": [
    {
      "law": "Signature Conservation",
      "type": "signature_mismatch",
      "severity": "error",
      "message": "Function calculate_total expects 2 arguments but called with 1",
      "file_path": "myapp/orders.py",
      "line_number": 35,
      "column_number": 12,
      "code_snippet": "    total = calculate_total(items)",
      "suggested_fix": "Add missing argument: calculate_total(items, False)"
    }
  ],
  "summary": {
    "signature_conservation": 1,
    "reference_integrity": 0,
    "data_flow_consistency": 0,
    "structural_integrity": 0
  },
  "total_violations": 1
}
```

**Use Cases:**
- After LLM edits code
- Before committing changes
- Continuous validation in CI/CD

---

### Category 4: Snapshots

#### 11. `create_snapshot`

Create a snapshot of current graph state.

**Parameters:**
- `description` (string, optional): Description of snapshot
- `tags` (array, optional): Tags for categorization

**Example:**
```json
{
  "description": "Before refactoring billing module",
  "tags": ["refactoring", "billing"]
}
```

**Returns:**
```json
{
  "snapshot_id": "snap_20250119_143022",
  "description": "Before refactoring billing module",
  "timestamp": "2025-01-19T14:30:22Z",
  "stats": {
    "total_nodes": 144,
    "total_edges": 215
  }
}
```

**Use Cases:**
- Before major refactoring
- Creating restore points
- Tracking code evolution

---

#### 12. `compare_snapshots`

Compare two snapshots to see what changed.

**Parameters:**
- `old_snapshot_id` (string, required): Earlier snapshot ID
- `new_snapshot_id` (string, required): Later snapshot ID

**Example:**
```json
{
  "old_snapshot_id": "snap_20250119_143022",
  "new_snapshot_id": "snap_20250119_150000"
}
```

**Returns:**
```json
{
  "comparison": {
    "nodes_added": [
      {
        "id": "func_new123",
        "type": "Function",
        "name": "new_helper_function",
        "location": "myapp/billing.py:120:0"
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
          }
        }
      }
    ],
    "edges_added": 3,
    "edges_removed": 0
  },
  "summary": {
    "total_changes": 4
  }
}
```

**Use Cases:**
- Review what LLM changed
- Validate refactoring results
- Generate change reports

---

#### 13. `list_snapshots`

List all available snapshots.

**Parameters:**
- `limit` (integer, optional): Maximum number to return (default: 20)

**Example:**
```json
{
  "limit": 10
}
```

**Returns:**
```json
{
  "snapshots": [
    {
      "snapshot_id": "snap_20250119_150000",
      "description": "After refactoring billing module",
      "timestamp": "2025-01-19T15:00:00Z",
      "tags": ["refactoring", "billing"]
    },
    {
      "snapshot_id": "snap_20250119_143022",
      "description": "Before refactoring billing module",
      "timestamp": "2025-01-19T14:30:22Z",
      "tags": ["refactoring", "billing"]
    }
  ],
  "total_snapshots": 2
}
```

**Use Cases:**
- Browse history
- Find specific snapshots
- Audit trail

---

## Complete LLM Workflow

### Scenario: Add a required parameter to a function

**Step 1: Query before editing**

LLM uses `find_function` to locate the target:
```json
{
  "name": "calculate_total"
}
```

**Step 2: Analyze impact**

LLM uses `analyze_impact`:
```json
{
  "entity_id": "func_abc123",
  "change_type": "modify"
}
```

Result shows 3 callers that will need updates.

**Step 3: Create snapshot**

LLM uses `create_snapshot`:
```json
{
  "description": "Before adding discount parameter"
}
```

**Step 4: Edit code**

LLM uses standard Edit tool to modify function:
```python
# Before
def calculate_total(items: list) -> float:
    return sum(item.price for item in items)

# After
def calculate_total(items: list, apply_discount: bool) -> float:
    total = sum(item.price for item in items)
    if apply_discount:
        total *= 0.9
    return total
```

**Step 5: Re-index**

LLM uses `index_codebase`:
```json
{
  "path": "/home/user/project/myapp/billing.py",
  "clear": false
}
```

**Step 6: Validate**

LLM uses `validate_codebase`:
```json
{
  "include_pyright": true
}
```

Result shows 3 violations (callers missing new argument).

**Step 7: Fix violations**

LLM uses Edit tool to update all 3 callers:
```python
# Old
total = calculate_total(items)

# New
total = calculate_total(items, True)
```

**Step 8: Re-index and validate again**

```json
{"path": "/home/user/project", "clear": false}
```

Then:
```json
{"include_pyright": true}
```

Result: 0 violations ✅

**Step 9: Create final snapshot**

```json
{
  "description": "After adding discount parameter - all callers updated"
}
```

**Step 10: Compare snapshots**

```json
{
  "old_snapshot_id": "snap_before",
  "new_snapshot_id": "snap_after"
}
```

Shows exactly what changed.

---

## Error Handling

All tools return consistent error format:

```json
{
  "error": {
    "code": "FUNCTION_NOT_FOUND",
    "message": "Function with ID 'func_xyz' does not exist",
    "details": {
      "searched_id": "func_xyz",
      "available_functions": 42
    }
  }
}
```

Common error codes:
- `FUNCTION_NOT_FOUND`
- `DATABASE_CONNECTION_ERROR`
- `INVALID_PARAMETER`
- `PARSING_ERROR`
- `SNAPSHOT_NOT_FOUND`

---

## Performance Considerations

### Indexing Performance

| Codebase Size | Files | Functions | Index Time |
|---------------|-------|-----------|------------|
| Small         | 10    | 50        | 1-2s       |
| Medium        | 50    | 250       | 5-10s      |
| Large         | 200   | 1000      | 30-60s     |

**Optimization tips:**
- Use `clear=false` for incremental updates
- Index specific files instead of entire directories
- Use `--limit` parameters where available

### Query Performance

All queries are optimized with Neo4j indexes:
- Function lookups: O(log n)
- Caller/callee queries: O(degree)
- Validation: O(changed nodes)

---

## Advanced Usage

### Custom Validation Rules

While the MCP server provides the 4 standard conservation laws, you can add custom rules:

```python
# In validators.py
def validate_custom_naming_convention(self):
    """Check that all public functions have docstrings."""
    query = """
    MATCH (f:Function {visibility: 'public'})
    WHERE f.docstring IS NULL
    RETURN f.qualified_name, f.location
    """
    results = self.db.execute_query(query)
    # Return violations
```

### Incremental Validation

Mark specific files as changed for faster validation:

```cypher
MATCH (n {file: 'myapp/billing.py'})
SET n.changed = true
```

Then run validation - only changed nodes and their dependents are checked.

---

## Troubleshooting

### MCP Server Won't Start

**Issue:** Server starts but Claude can't connect

**Solution:**
1. Check Python path in MCP config
2. Verify Neo4j is running: `docker ps`
3. Test database connection: `python -c "from neo4j import GraphDatabase; ..."`
4. Check logs in Claude Code output panel

### Indexing Fails

**Issue:** `index_codebase` returns parsing errors

**Solution:**
1. Ensure Python files are syntactically valid
2. Check file encoding (must be UTF-8)
3. Review error details in response
4. Try indexing individual files to isolate issue

### Validation Shows False Positives

**Issue:** Valid code reported as violations

**Solution:**
1. Check for signature-transforming decorators
2. Update `SIGNATURE_TRANSFORMING_DECORATORS` in validators.py
3. Review parameter counting (required vs optional)
4. Check pyright configuration

### Snapshots Not Persisting

**Issue:** Snapshots disappear after restart

**Solution:**
- Snapshots are in-memory only
- Implement persistence (see `snapshot.py`)
- Use git integration for permanent history

---

## Best Practices

### 1. Always Create Snapshots

Before any major change:
```json
{"description": "Before [specific change]"}
```

### 2. Validate Incrementally

After each LLM edit:
```json
{"include_pyright": false}  // Fast check
```

Full validation before commit:
```json
{"include_pyright": true}   // Deep check
```

### 3. Use Impact Analysis

Before modifying shared functions:
```json
{
  "entity_id": "func_id",
  "change_type": "modify"
}
```

### 4. Index Incrementally

Don't clear database unnecessarily:
```json
{"path": "specific/file.py", "clear": false}
```

### 5. Tag Snapshots

Use meaningful tags:
```json
{
  "description": "Refactored auth module",
  "tags": ["auth", "refactoring", "security"]
}
```

---

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/validate.yml
- name: Start Neo4j
  run: docker run -d -p 7687:7687 neo4j:latest

- name: Index and Validate
  run: |
    python backend/codegraph/mcp_server.py < commands.json
```

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Index changed files
python -c "
from codegraph import index_codebase, validate_codebase
index_codebase('.')
report = validate_codebase()
if report['total_violations'] > 0:
    print('Validation failed!')
    exit(1)
"
```

### VSCode Extension

```javascript
// Use MCP client to call CodeGraph
const client = new MCPClient('codegraph');
const result = await client.call('validate_codebase', {
  include_pyright: true
});
// Show violations in Problems panel
```

---

## API Versioning

Current version: **1.0.0**

The MCP server follows semantic versioning:
- Major: Breaking changes to tool signatures
- Minor: New tools or non-breaking enhancements
- Patch: Bug fixes

---

## Future Enhancements

Planned features:
- [ ] Cross-language support (JavaScript, TypeScript)
- [ ] Real-time graph updates via WebSocket
- [ ] Persistent snapshot storage
- [ ] Custom query tool for Cypher
- [ ] Batch operations for multiple functions
- [ ] Graph visualization tool integration

---

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Neo4j Cypher Documentation](https://neo4j.com/docs/cypher-manual/)
- [Conservation Laws Theory](../theory/THEORY_SUMMARY.md)
- [Graph Schema](./schema.md)
- [API Reference](../guides/API_REFERENCE.md)

---

## Support

For issues or questions:
- GitHub Issues: [repository/issues]
- Documentation: [docs/]
- Examples: [docs/examples/]

---

**Last Updated:** 2025-01-19
**Version:** 1.0.0
**Status:** Production Ready
