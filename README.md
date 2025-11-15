# CodeGraph - Graph Database for Code with Conservation Laws

A complete solution for analyzing Python codebases with graph database technology and conservation law validation. Now with a **FastAPI backend** for building visualization frontends!

## What is CodeGraph?

CodeGraph builds a **Neo4j graph database** from your Python code, tracking functions, classes, variables, and their relationships. It enforces **4 conservation laws** to ensure that code modifications (by humans or LLMs) don't break existing relationships.

### The 4 Conservation Laws

1. **Signature Conservation** - Function signatures must match all call sites
2. **Reference Integrity** - All references must resolve to valid entities
3. **Data Flow Consistency** - Types must be compatible across calls
4. **Structural Integrity** - Graph structure must remain valid

## Project Structure

```
graph-db-for-codebase/
├── backend/                      # 🆕 Everything is now in backend/
│   ├── codegraph/               # Core library
│   │   ├── db.py                # Neo4j connection
│   │   ├── parser.py            # Python AST parser
│   │   ├── builder.py           # Graph builder
│   │   ├── query.py             # Query interface
│   │   ├── validators.py        # Conservation laws
│   │   └── cli.py               # CLI tool
│   ├── app/                     # FastAPI backend
│   │   ├── main.py              # REST API
│   │   ├── models.py            # Pydantic models
│   │   ├── database.py          # DB manager
│   │   └── config.py            # Settings
│   ├── examples/                # Example Python files
│   ├── requirements.txt         # Dependencies
│   ├── Dockerfile               # Docker image
│   ├── run.py                   # Dev server
│   └── GETTING_STARTED.md       # Detailed guide
├── docker-compose.yml           # Full stack (Neo4j + Backend)
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

- **[GETTING_STARTED.md](backend/GETTING_STARTED.md)** - Complete setup guide
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation (when running)
- **[schema.md](backend/schema.md)** - Graph schema details
- **[PROJECT_SUMMARY.md](backend/PROJECT_SUMMARY.md)** - Architecture overview

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

## 🎯 What's New

This version restructures the project with:

- ✅ **Complete backend in one directory** (`backend/`)
- ✅ **FastAPI REST API** for frontend integration
- ✅ **Docker Compose** for easy deployment
- ✅ **Graph export endpoints** for visualization
- ✅ **CORS configuration** for frontend access
- ✅ **Pydantic models** for type safety
- ✅ **Comprehensive API documentation**

## 🚧 Coming Soon

- Frontend examples (React, Vue, Svelte)
- WebSocket support for real-time updates
- Multi-language support (JavaScript, TypeScript, Java)
- GraphML/DOT export
- CLI improvements

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

**Ready to visualize your codebase?** Start with [GETTING_STARTED.md](backend/GETTING_STARTED.md)!
