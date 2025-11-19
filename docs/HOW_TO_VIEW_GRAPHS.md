# How to View Graphs in Neo4j - Complete Guide

## Quick Start (3 Steps)

### Step 1: Index a File Using the API

```bash
# Using curl (Windows PowerShell)
curl -X POST "http://localhost:8000/index" `
  -H "Content-Type: application/json" `
  -d '{\"path\": \"D:\\dev\\graph db for codebase\\backend\\examples\\connected_example.py\", \"clear\": true}'

# Using curl (Git Bash / Linux style)
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{"path": "D:\\dev\\graph db for codebase\\backend\\examples\\connected_example.py", "clear": true}'
```

### Step 2: Open Neo4j Browser

Open your browser and go to:
```
http://localhost:7474
```

**Login credentials:**
- Username: `neo4j`
- Password: `password`

### Step 3: Run Cypher Queries

In the Neo4j Browser query box, try these queries:

```cypher
// See all nodes
MATCH (n) RETURN n LIMIT 50

// See function call graph (via CallSite nodes)
MATCH (f:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(c:Function)
RETURN f, cs, c

// See functions with parameters
MATCH (f:Function)-[r:HAS_PARAMETER]->(p:Parameter)
RETURN f, r, p LIMIT 25
```

---

## Custom Viewer (Neovis)

Need more control over how the graph is rendered? Use the bundled Neovis viewer which hides noisy edges (like `HAS_CALLSITE`) and draws type nodes as hollow circles.

1. From the repo root run a lightweight static server (or open the file directly in a browser):
   ```bash
   python -m http.server 8081
   ```
2. Open [http://localhost:8081/graph-viewer.html](http://localhost:8081/graph-viewer.html).
3. Keep the default bolt credentials (`neo4j` / `password`) or update them in the form, edit the Cypher textarea if needed, and click **Render**.

The viewer talks straight to Neo4j, so any query you run in the text box will render with the custom styling (type nodes as hollow circles, callsite edges hidden by default). Tweak `graph-viewer.html` if you want to adjust colors or behaviors.

---

## Complete API Guide

### Base URL
```
http://localhost:8000
```

### Available Endpoints

#### 1. **Index Codebase** - `POST /index`

**Purpose**: Parse and index Python files into Neo4j

**Request:**
```json
{
  "path": "C:/path/to/file.py",  // Absolute path to file or directory
  "clear": true                    // Optional: clear database first (default: false)
}
```

**Example (PowerShell):**
```powershell
$body = @{
    path = "D:\dev\graph db for codebase\backend\examples\example_code.py"
    clear = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/index" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

**Example (curl):**
```bash
curl -X POST "http://localhost:8000/index" \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/file.py", "clear": true}'
```

**Response:**
```json
{
  "success": true,
  "entities_indexed": 29,
  "relationships_created": 31,
  "statistics": {
    "Function": 14,
    "Parameter": 15,
    "Relationships": 31
  }
}
```

---

#### 2. **Get Statistics** - `GET /stats`

**Purpose**: Get database statistics

**Example:**
```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "Function": 14,
  "Class": 0,
  "Variable": 0,
  "Parameter": 15,
  "Module": 0,
  "Type": 0,
  "Relationships": 31
}
```

---

#### 3. **Search Functions** - `GET /search`

**Purpose**: Search for functions by pattern

**Parameters:**
- `pattern`: Regex pattern to search for
- `entity_type`: Optional (Function, Class, Variable, Parameter)

**Example:**
```bash
curl "http://localhost:8000/search?pattern=calculate.*&entity_type=Function"
```

**Response:**
```json
{
  "results": [
    {
      "id": "abc123",
      "name": "calculate_total",
      "qualified_name": "example.calculate_total",
      "signature": "calculate_total(items: list) -> float"
    }
  ],
  "count": 1
}
```

---

#### 4. **Get Function Details** - `GET /functions/{function_id}`

**Purpose**: Get complete function information

**Example:**
```bash
curl "http://localhost:8000/functions/abc123"
```

**Response:**
```json
{
  "function": {
    "id": "abc123",
    "name": "calculate_total",
    "signature": "calculate_total(items: list) -> float",
    "return_type": "float",
    "visibility": "public"
  },
  "parameters": [
    {
      "param": {
        "name": "items",
        "type_annotation": "list",
        "position": 0
      }
    }
  ]
}
```

---

#### 5. **Validate Codebase** - `POST /validate`

**Purpose**: Check all 4 conservation laws

**Example:**
```bash
curl -X POST "http://localhost:8000/validate"
```

**Response:**
```json
{
  "total_violations": 1,
  "errors": 1,
  "warnings": 0,
  "safe_to_commit": false,
  "violations": [
    {
      "violation_type": "signature_mismatch",
      "severity": "error",
      "message": "Function calculate expects 2 arguments but is called with 3",
      "file_path": "example.py",
      "line_number": 55,
      "column_number": 4
    }
  ]
}
```

---

## Neo4j Browser Guide

### Opening Neo4j Browser

1. Open browser: `http://localhost:7474`
2. Login: `neo4j` / `password`
3. You'll see a query box at the top

### Essential Cypher Queries

#### View All Nodes
```cypher
MATCH (n)
RETURN n
LIMIT 50
```

#### View Function Call Graph
```cypher
MATCH (f:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(c:Function)
RETURN f, cs, c
```
This shows which functions call which other functions via CallSite nodes.

#### View Functions with Parameters
```cypher
MATCH (f:Function)-[r:HAS_PARAMETER]->(p:Parameter)
RETURN f, r, p
LIMIT 25
```
This shows the function-parameter relationships.

#### Find Specific Function
```cypher
MATCH (f:Function {name: "calculate_total"})
RETURN f
```

#### See What Calls a Function
```cypher
MATCH (caller:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(f:Function {name: "calculate_total"})
RETURN caller, cs, f
```

#### See What a Function Calls
```cypher
MATCH (f:Function {name: "main"})-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(callee:Function)
RETURN f, cs, callee
```

#### Full Dependency Tree (3 levels deep)
```cypher
MATCH path = (f:Function {name: "main"})-[:HAS_CALLSITE|RESOLVES_TO*2..6]->(other:Function)
WHERE other:Function
RETURN path
```

#### View Classes and Their Methods
```cypher
MATCH (c:Class)
OPTIONAL MATCH (c)-[:DECLARES]->(m:Function)
RETURN c, m
```

#### Complete Graph
```cypher
MATCH (n)-[r]->(m)
RETURN n, r, m
LIMIT 100
```

---

## Step-by-Step Example Workflow

### Example: Analyzing connected_example.py

**1. Index the file:**
```powershell
$body = @{
    path = "D:\dev\graph db for codebase\backend\examples\connected_example.py"
    clear = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/index" -Method POST -ContentType "application/json" -Body $body
```

**2. Get statistics:**
```bash
curl http://localhost:8000/stats
```

**3. Open Neo4j Browser:**
- Go to http://localhost:7474
- Login: neo4j / password

**4. Visualize the call graph:**
```cypher
MATCH (f:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(c:Function)
RETURN f, cs, c
```

**5. Find the main function:**
```cypher
MATCH (f:Function {name: "main"})
RETURN f
```

**6. See what main() calls:**
```cypher
MATCH (f:Function {name: "main"})-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(callee:Function)
RETURN f, cs, callee
```

**7. View full call chain from main:**
```cypher
MATCH path = (f:Function {name: "main"})-[:HAS_CALLSITE|RESOLVES_TO*2..8]->(other:Function)
WHERE other:Function
RETURN path
```

**8. Validate the code:**
```bash
curl -X POST "http://localhost:8000/validate"
```

---

## Visualizing Different Examples

### Example 1: Simple Calculator (example_code.py)

**Index:**
```powershell
$body = @{
    path = "D:\dev\graph db for codebase\backend\examples\example_code.py"
    clear = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/index" -Method POST -ContentType "application/json" -Body $body
```

**View in Neo4j:**
```cypher
// See the Calculator class and its methods
MATCH (c:Class {name: "Calculator"})
OPTIONAL MATCH (f:Function)
WHERE f.qualified_name CONTAINS "Calculator"
RETURN c, f

// See the function call chain
MATCH path = (f:Function {name: "process_data"})-[:HAS_CALLSITE|RESOLVES_TO*1..]->(other:Function)
RETURN path
```

### Example 2: Violations (example_violations.py)

**Index:**
```powershell
$body = @{
    path = "D:\dev\graph db for codebase\backend\examples\example_violations.py"
    clear = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/index" -Method POST -ContentType "application/json" -Body $body
```

**View in Neo4j:**
```cypher
// See the problematic function
MATCH (f:Function {name: "calculate"})
MATCH (caller:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(f)
RETURN caller, cs, f
```

**Check for violations:**
```bash
curl -X POST "http://localhost:8000/validate"
```
This will show the signature mismatch!

### Example 3: Complex Graph (connected_example.py)

**Index:**
```powershell
$body = @{
    path = "D:\dev\graph db for codebase\backend\examples\connected_example.py"
    clear = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/index" -Method POST -ContentType "application/json" -Body $body
```

**View in Neo4j:**
```cypher
// See the entire call graph
MATCH (f:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(c:Function)
RETURN f, cs, c

// Find leaf functions (don't call anything)
MATCH (f:Function)
WHERE NOT (f)-[:HAS_CALLSITE]->()
RETURN f.name as leaf_function

// Find entry points (not called by anyone)
MATCH (f:Function)
WHERE NOT (:CallSite)-[:RESOLVES_TO]->(f)
RETURN f.name as entry_point
```

---

## Neo4j Browser Tips

### Changing Visualization Style

1. **Click on a node type** (e.g., "Function") in the legend
2. **Choose "Caption"** to select which property to display
3. **Choose "Size"** to size nodes by property
4. **Choose "Color"** to color by property

### Recommended Settings

- **Function nodes**:
  - Caption: `name`
  - Color: by `visibility` (public/private)

- **Parameter nodes**:
  - Caption: `name`
  - Size: fixed small

- **Relationship labels**:
  - Show relationship type
  - Show `arg_count` for CallSite nodes

### Exploring Interactively

1. **Double-click a node** to expand its relationships
2. **Click and drag** to move nodes
3. **Right-click** for more options
4. **Use mouse wheel** to zoom
5. **Click background** to deselect

---

## Common Queries Cheat Sheet

```cypher
// 1. Count nodes by type
MATCH (n) RETURN labels(n) as type, count(*) as count

// 2. Find functions with most parameters
MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
RETURN f.name, count(p) as param_count
ORDER BY param_count DESC

// 3. Find functions that don't call anything
MATCH (f:Function)
WHERE NOT (f)-[:HAS_CALLSITE]->()
RETURN f.name

// 4. Find most called functions
MATCH (cs:CallSite)-[:RESOLVES_TO]->(f:Function)
RETURN f.name, count(cs) as call_count
ORDER BY call_count DESC

// 5. Find parameter types
MATCH (p:Parameter)
WHERE p.type_annotation IS NOT NULL
RETURN DISTINCT p.type_annotation, count(*) as usage
ORDER BY usage DESC

// 6. Find functions with missing type annotations
MATCH (f:Function)
WHERE f.return_type IS NULL
RETURN f.name

// 7. Shortest path between two functions
MATCH path = shortestPath(
  (start:Function {name: "main"})-[:HAS_CALLSITE|RESOLVES_TO*]-(end:Function {name: "read_file"})
)
RETURN path

// 8. All paths of specific length (2 calls = 4 hops through CallSites)
MATCH path = (f:Function {name: "main"})-[:HAS_CALLSITE|RESOLVES_TO*4]->(other:Function)
WHERE other:Function
RETURN path
```

---

## Troubleshooting

### Problem: "Connection refused" when accessing API

**Solution:**
```bash
# Check if backend is running
docker ps

# If not running, start it
docker-compose up backend
```

### Problem: "Neo4j not accessible" at localhost:7474

**Solution:**
```bash
# Check if Neo4j is running
docker ps

# If not running, start it
docker-compose up neo4j

# Wait for it to fully start (about 10 seconds)
```

### Problem: "Empty graph" after indexing

**Check:**
```bash
# Verify file path is correct and absolute
# On Windows: D:\path\to\file.py
# On Linux: /path/to/file.py

# Check API response
curl http://localhost:8000/stats
```

### Problem: Can't see relationships in Neo4j

**Try:**
```cypher
// Make sure relationships exist
MATCH ()-[r]->() RETURN type(r), count(*) as count

// If zero, re-index the file
```

---

## Advanced: Using Python Directly

If you prefer Python over API:

```python
from codegraph.db import CodeGraphDB
from codegraph.parser import PythonParser
from codegraph.builder import GraphBuilder

# Connect
db = CodeGraphDB('bolt://localhost:7687', 'neo4j', 'password')
db.clear_database()
db.initialize_schema()

# Parse
parser = PythonParser()
entities, rels = parser.parse_file('path/to/file.py')

# Build
builder = GraphBuilder(db)
builder.build_graph(entities, rels)

# Now view in Neo4j Browser!
db.close()
```

---

## Quick Reference Card

| Task | API Endpoint | Cypher Query |
|------|--------------|--------------|
| Index file | `POST /index` | N/A |
| Get stats | `GET /stats` | `MATCH (n) RETURN labels(n), count(*)` |
| Find function | `GET /search?pattern=name` | `MATCH (f:Function {name: "name"})` |
| See calls | N/A | `MATCH (f)-[:HAS_CALLSITE]->(cs)-[:RESOLVES_TO]->(c) RETURN f,cs,c` |
| Validate | `POST /validate` | N/A |
| View all | N/A | `MATCH (n)-[r]->(m) RETURN n,r,m` |

---

**Now try it yourself!**

1. Pick an example file
2. Index it using the API
3. Open Neo4j Browser
4. Run the Cypher queries
5. Explore the graph interactively!
