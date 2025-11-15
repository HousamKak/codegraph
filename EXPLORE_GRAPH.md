# Exploring the CodeGraph of Itself! 🎉

We just indexed the CodeGraph project's own code into the graph database. Now you can explore it!

## What Was Indexed

**Location:** `/app/codegraph` (the core library)

**Statistics:**
- **66 Functions** - All the functions in the codebase
- **13 Classes** - PythonParser, GraphBuilder, QueryInterface, etc.
- **32 Variables** - Module and class-level variables
- **154 Parameters** - All function parameters
- **155 Relationships** - Function calls, parameter connections, etc.

## How to Explore

### Option 1: Neo4j Browser (Visual)

1. **Open Neo4j Browser:**
   ```
   http://localhost:7474
   ```
   Login: `neo4j` / `password`

2. **See all nodes:**
   ```cypher
   MATCH (n) RETURN n LIMIT 25
   ```

3. **See all functions:**
   ```cypher
   MATCH (f:Function) RETURN f LIMIT 20
   ```

4. **See function call graph:**
   ```cypher
   MATCH (f:Function)-[r:CALLS]->(callee:Function)
   RETURN f, r, callee
   LIMIT 30
   ```

5. **Find the PythonParser class and its methods:**
   ```cypher
   MATCH (f:Function)
   WHERE f.qualified_name CONTAINS 'PythonParser'
   RETURN f.name, f.signature
   ORDER BY f.name
   ```

6. **See functions with most parameters:**
   ```cypher
   MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
   WITH f, count(p) as param_count
   RETURN f.name, param_count
   ORDER BY param_count DESC
   LIMIT 10
   ```

7. **Find all private methods:**
   ```cypher
   MATCH (f:Function)
   WHERE f.visibility = 'private'
   RETURN f.name, f.qualified_name
   LIMIT 20
   ```

8. **See class hierarchy:**
   ```cypher
   MATCH (c:Class)
   RETURN c.name, c.qualified_name
   ```

### Option 2: API (Programmatic)

**Search for functions:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "parse", "entity_type": "Function"}'
```

**Get graph data for visualization:**
```bash
curl -s http://localhost:8000/graph?limit=50 > codegraph.json
```

**Search for classes:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "Builder", "entity_type": "Class"}'
```

**Get all functions:**
```bash
curl http://localhost:8000/functions
```

## Interesting Queries

### 1. Find the most complex function (most parameters)

**Neo4j Browser:**
```cypher
MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
WITH f, count(p) as params
RETURN f.name, f.signature, params
ORDER BY params DESC
LIMIT 5
```

### 2. Find functions that don't call anything (leaf functions)

```cypher
MATCH (f:Function)
WHERE NOT (f)-[:CALLS]->()
RETURN f.name, f.qualified_name
LIMIT 10
```

### 3. Find functions called by many others (highly used)

```cypher
MATCH (f:Function)<-[:CALLS]-(caller)
WITH f, count(caller) as callers
WHERE callers > 1
RETURN f.name, callers
ORDER BY callers DESC
```

### 4. See the full call chain for parse_file

```cypher
MATCH path = (f:Function {name: 'parse_file'})-[:CALLS*1..3]->(callee)
RETURN path
LIMIT 20
```

### 5. Find all validator functions

```cypher
MATCH (f:Function)
WHERE f.qualified_name CONTAINS 'validator'
RETURN f.name, f.signature
```

### 6. Get statistics about the codebase

```cypher
// Function count by visibility
MATCH (f:Function)
RETURN f.visibility, count(f) as count

// Async vs sync functions
MATCH (f:Function)
RETURN f.is_async, count(f) as count

// Functions with type annotations
MATCH (f:Function)
WHERE f.return_type IS NOT NULL
RETURN count(f) as typed_functions
```

## Example: Explore PythonParser

The PythonParser is the heart of the system. Let's explore it:

**1. Find all PythonParser methods:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "PythonParser", "entity_type": "Function"}'
```

**2. In Neo4j Browser, visualize its methods:**
```cypher
MATCH (f:Function)
WHERE f.qualified_name CONTAINS 'PythonParser'
RETURN f
```

**3. See what parse_file calls:**
```cypher
MATCH (f:Function {name: 'parse_file'})-[:CALLS*1..2]->(callee)
RETURN f, callee
```

## Example: Graph Export for Visualization

**Get the full graph as JSON:**
```bash
curl -s http://localhost:8000/graph?limit=100 > codegraph.json
```

This gives you:
```json
{
  "nodes": [
    {
      "id": "abc123",
      "labels": ["Function"],
      "properties": {
        "name": "parse_file",
        "signature": "parse_file(self, file_path: str) -> Tuple[...]",
        "qualified_name": "...PythonParser.parse_file"
      }
    }
  ],
  "edges": [
    {
      "source": "abc123",
      "target": "def456",
      "type": "CALLS"
    }
  ]
}
```

**Use this with D3.js, Vis.js, etc. to build your visualizer!**

## Real-World Example: Impact Analysis

Let's say you want to change the `parse_file` method. First, check its impact:

**1. Find the function:**
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "parse_file", "entity_type": "Function"}'
```

**2. Get its ID (from response), then check impact:**
```bash
curl -X POST http://localhost:8000/impact \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "26b6af6b575ebf50", "change_type": "modify"}'
```

This shows **what would break** if you change it!

## Fun Exploration

### Code Statistics

```bash
# Total entities
curl -s http://localhost:8000/stats

# Returns:
# {
#   "Function": 66,
#   "Class": 13,
#   "Parameter": 154,
#   ...
# }
```

### Most Connected Functions

In Neo4j Browser:
```cypher
MATCH (f:Function)
OPTIONAL MATCH (f)-[r]-()
WITH f, count(r) as connections
RETURN f.name, connections
ORDER BY connections DESC
LIMIT 10
```

### Dependency Graph

```cypher
MATCH (f:Function)-[:CALLS]->(dep:Function)
WHERE f.qualified_name CONTAINS 'parse'
RETURN f.name as caller, dep.name as dependency
```

## Next Steps

1. **Explore in Neo4j Browser** - Visual, interactive
   - http://localhost:7474
   - Try the queries above!

2. **Query via API** - Programmatic access
   - Perfect for building your frontend

3. **Export graph data** - Build custom visualizations
   - `curl http://localhost:8000/graph?limit=100`

4. **Index your own project**
   ```bash
   curl -X POST http://localhost:8000/index \
     -H "Content-Type: application/json" \
     -d '{"path": "/path/to/your/project", "clear": true}'
   ```

## Cool Insights You Can Find

- Which functions are most reused?
- Which functions have the most dependencies?
- What's the longest call chain?
- Which code has no type annotations?
- What functions are never called (dead code)?
- What's the complexity distribution?

**Go explore!** 🚀

Open http://localhost:7474 and start running Cypher queries!
