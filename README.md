# CodeGraph - Graph Database for Code Analysis

A **read-only analysis tool** that provides LLMs with "eyes" to see code relationships using Neo4j graph database. It validates code changes against **4 conservation laws** through snapshot comparison.

## What is CodeGraph?

CodeGraph indexes Python code into a **Neo4j graph database**, capturing functions, classes, variables, and their relationships. It provides analysis, querying, and validation capabilities - the LLM does ALL code editing, while CodeGraph provides insights.

### The 4 Conservation Laws

1. **Signature Conservation** - Function signatures must match all call sites
2. **Reference Integrity** - All references must resolve to valid entities
3. **Data Flow Consistency** - Types must be compatible across calls
4. **Structural Integrity** - Graph structure must remain valid

## Project Structure

```
graph-db-for-codebase/
├── backend/
│   ├── codegraph/               # Core library
│   │   ├── db.py                # Neo4j connection
│   │   ├── parser.py            # Python AST parser
│   │   ├── builder.py           # Graph builder
│   │   ├── query.py             # Query interface
│   │   ├── validators.py        # Conservation law validators
│   │   ├── snapshot.py          # Snapshot comparison
│   │   ├── mcp_server.py        # MCP server (read-only tools)
│   │   └── cli.py               # CLI tool
│   ├── app/                     # FastAPI backend
│   │   ├── main.py              # REST API
│   │   ├── models.py            # Pydantic models
│   │   ├── database.py          # DB manager
│   │   └── config.py            # Settings
│   ├── examples/                # Example files
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml           # Neo4j + Backend
├── DOCKER_COMMANDS.md          # Docker reference
└── README.md                    # This file
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

Start both Neo4j and the backend API with one command:

```bash
# From project root
docker-compose up -d

# Access:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Neo4j: http://localhost:7474
```

### Option 2: Run Locally

```bash
# Start Neo4j
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password neo4j:latest

# Install and run backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # Configure if needed
python run.py

# API will be at http://localhost:8000
```

### Next: Index Your Code

```bash
# Index example code
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "./backend/examples", "clear": true}'

# Get graph data for visualization
curl http://localhost:8000/graph?limit=100
```

## 📊 Backend API

The FastAPI backend provides REST endpoints for:

- **Indexing**: Parse and index Python codebases
- **Querying**: Find functions, classes, dependencies
- **Validation**: Check conservation laws
- **Graph Export**: Get data for visualization frontends
- **Custom Queries**: Execute Cypher queries

### Key Endpoints

```bash
GET  /health                          # Health check
POST /index                           # Index codebase
GET  /graph?limit=100                 # Get graph data
GET  /graph/function/{id}?depth=2     # Get subgraph
POST /search                          # Search entities
GET  /validate                        # Validate code
GET  /stats                           # Database stats
POST /query                           # Custom Cypher query
```

**Full Documentation**: http://localhost:8000/docs

## 🤖 LLM Workflow: Read-Only Analysis

CodeGraph is a **read-only analysis tool** - it provides "eyes" for LLMs to see code relationships.

### How It Works

```
1. LLM edits code (using its own tools)
2. Graph DB re-indexes → New snapshot
3. Compare old vs new snapshots
4. Detect violations (broken connections)
5. LLM sees violations → Fixes code
6. Repeat until clean
```

### Features

✅ **Snapshot comparison** - Before/after graph state diffing
✅ **Precise violation detection** - Exact file:line locations with code snippets
✅ **Conservation law validation** - 4 laws to ensure code integrity
✅ **MCP protocol** - Direct LLM tool integration (read-only)
✅ **Impact analysis** - See what breaks before making changes

### MCP Tools Available (Read-Only)

CodeGraph provides 13 analysis tools via MCP:

**Indexing & Stats:**
1. **index_codebase** - Parse and index Python code
2. **get_graph_stats** - Get database statistics

**Querying:**
3. **find_function** - Find functions by name
4. **get_function_details** - Get function signature and parameters
5. **get_function_callers** - Find who calls this function
6. **get_function_callees** - Find what this function calls
7. **get_function_dependencies** - Full dependency tree
8. **search_code** - Search for entities by pattern

**Analysis:**
9. **analyze_impact** - See what breaks if you change/delete a function
10. **validate_codebase** - Check all conservation laws

**Snapshots:**
11. **create_snapshot** - Create snapshot of current graph state
12. **compare_snapshots** - Compare two snapshots to detect changes
13. **list_snapshots** - List all snapshots

### Example Workflow

```bash
# 1. Index codebase
curl -X POST http://localhost:8000/index \
  -d '{"path": "./backend/examples", "clear": true}'

# 2. Create baseline snapshot
curl -X POST http://localhost:8000/snapshot/create?description=before_edit

# 3. LLM edits code using its own tools (Edit, Write, etc.)

# 4. Re-index to capture changes
curl -X POST http://localhost:8000/index \
  -d '{"path": "./backend/examples"}'

# 5. Create new snapshot
curl -X POST http://localhost:8000/snapshot/create?description=after_edit

# 6. Compare snapshots to see what changed
curl -X POST http://localhost:8000/snapshot/compare \
  -d '{"old_snapshot_id": "abc123", "new_snapshot_id": "def456"}'

# 7. Validate for violations
curl http://localhost:8000/validate
```

## 🎨 Frontend Integration

The backend returns graph data in a format ready for visualization libraries:

### React + D3.js

```javascript
fetch('http://localhost:8000/graph?limit=100')
  .then(res => res.json())
  .then(({ nodes, edges }) => {
    // Use D3.js to visualize nodes and edges
  });
```

### Vue + Vis.js

```javascript
const graph = await fetch('http://localhost:8000/graph?limit=100').then(r => r.json());
const data = {
  nodes: graph.nodes.map(n => ({ id: n.id, label: n.properties.name })),
  edges: graph.edges.map(e => ({ from: e.source, to: e.target }))
};
// Pass to Vis.js Network
```

### Any Framework + Cytoscape.js, Sigma.js, etc.

The API returns standard `{nodes, edges}` format compatible with most graph libraries.

## 💡 Use Cases

### For LLM Code Generation
- Query graph before modifications to understand context
- Validate generated code against conservation laws
- Ensure changes don't break existing relationships

### For Developers
- **Impact Analysis**: See what changes affect before making them
- **Code Navigation**: Visualize call graphs and dependencies
- **Refactoring**: Safe renaming and signature changes
- **Documentation**: Auto-generated from graph structure

### For Teams
- **Code Review**: Automated validation of changes
- **Onboarding**: Visual exploration of codebase
- **Quality**: Continuous conservation law checking

## 📖 Documentation

- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation (when running)
- **[DOCKER_COMMANDS.md](DOCKER_COMMANDS.md)** - Docker reference commands
- **[schema.md](backend/schema.md)** - Graph schema details

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         Frontend (Your App)              │
│    React / Vue / Svelte / etc.          │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
               ▼
┌─────────────────────────────────────────┐
│         FastAPI Backend                  │
│  - REST API Endpoints                    │
│  - Graph Queries                         │
│  - Conservation Validators               │
└──────────────┬──────────────────────────┘
               │ Bolt Protocol
               ▼
┌─────────────────────────────────────────┐
│           Neo4j Database                 │
│  Nodes: Function, Class, Variable        │
│  Edges: CALLS, REFERENCES, etc.          │
└─────────────────────────────────────────┘
```

## 🔧 Configuration

Create `backend/.env`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 📊 Example: Full Workflow

```bash
# 1. Start services
docker-compose up -d

# 2. Index your codebase
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/project", "clear": true}'

# 3. Get statistics
curl http://localhost:8000/stats

# 4. Search for a function
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "MyFunction", "entity_type": "Function"}'

# 5. Get graph for visualization
curl http://localhost:8000/graph?limit=50 > graph.json

# 6. Validate conservation laws
curl http://localhost:8000/validate

# 7. Analyze impact of a change
curl -X POST http://localhost:8000/impact \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "abc123", "change_type": "delete"}'
```

## 🎯 Key Features

- ✅ **Read-only analysis** - LLM does editing, CodeGraph provides insights
- ✅ **Snapshot comparison** - Detect what changed between versions
- ✅ **Conservation laws** - 4 laws to ensure code integrity
- ✅ **MCP protocol** - 13 tools for LLM integration
- ✅ **FastAPI backend** - REST API for all operations
- ✅ **Docker Compose** - Easy deployment

## 🤝 Contributing

Contributions welcome! The project is now structured for easy extension:

1. Core library: `backend/codegraph/`
2. API endpoints: `backend/app/main.py`
3. Data models: `backend/app/models.py`

## 📄 License

MIT License

## 🙏 Credits

Built with:
- [Neo4j](https://neo4j.com/) - Graph database
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Pydantic](https://pydantic.dev/) - Data validation
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

---

**Ready to analyze your codebase?** Run `docker-compose up -d` and visit http://localhost:8000/docs
