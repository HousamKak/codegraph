# CodeGraph - Quick Start Guide

Complete Software Physics system for analyzing codebases as semantic graphs.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Frontend      │─────→│   FastAPI        │─────→│   Neo4j         │
│   (React)       │      │   Backend        │      │   Database      │
│   Port 5173     │      │   Port 8000      │      │   Port 7687     │
└─────────────────┘      └──────────────────┘      └─────────────────┘
```

## Prerequisites

1. **Neo4j Database**
   - Download from https://neo4j.com/download/
   - Or use Docker: `docker run -p 7474:7474 -p 7687:7687 neo4j:latest`
   - Default credentials: neo4j/neo4j (change on first login)

2. **Python 3.8+**

3. **Node.js 16+**

## Setup

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment (create .env file)
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USER=neo4j
# NEO4J_PASSWORD=your_password
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (already has .env)
# VITE_API_BASE_URL=http://localhost:8000
```

## Running the System

### Terminal 1: Start Backend

```bash
cd backend
venv\Scripts\activate
python run.py
```

Backend will be available at: http://localhost:8000

### Terminal 2: Start Frontend

```bash
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:5173

## First Steps

### 1. Index Your Codebase

Using the backend API:

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "path/to/your/python/project", "clear": true}'
```

Or use the MCP server tools if you have Claude Code.

### 2. Create a Snapshot

```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Initial state"
```

### 3. Open Frontend

Navigate to http://localhost:5173 and you'll see:
- **Graph View**: Your codebase as an interactive graph
- **History Panel**: Timeline of snapshots
- **Inspector Panel**: Click nodes to see details
- **Query Panel**: Execute Cypher queries

## Key Features

### Graph Visualization
- **Node Types**: Modules, Classes, Functions, Variables, Parameters, CallSites, Types, Decorators
- **Edge Types**: CONTAINS, CALLS, RESOLVES_TO, USES, DEFINES, INHERITS, etc.
- **Color-coded** by type with interactive controls

### Snapshot Management
- Create snapshots before making changes
- Compare snapshots to see diffs
- Timeline view like VS Code history
- Tag important snapshots

### Diff View
- **Side-by-side**: Compare before/after graphs
- **Unified**: See all changes in one view
- **Highlighting**:
  - Green = Added
  - Red = Removed
  - Orange = Modified

### Conservation Laws
- **S Law** (Structural): Graph conforms to schema
- **R Law** (Referential): All references resolve
- **T Law** (Typing): Type annotations consistent

### Cypher Queries
Example queries:
```cypher
// All nodes
MATCH (n) RETURN n LIMIT 100

// Changed nodes
MATCH (n) WHERE n.changed = true RETURN n

// Function calls
MATCH (f:Function)-[r:CALLS]->(g:Function) RETURN f, r, g

// Resolved calls
MATCH (c:CallSite)-[r:RESOLVES_TO]->(f:Function) RETURN c, r, f

// Class inheritance
MATCH (c:Class)-[r:INHERITS]->(b:Class) RETURN c, r, b
```

## Workflow Example

1. **Initial State**
   ```bash
   # Index codebase
   curl -X POST http://localhost:8000/index -d '{"path": "./my_project"}'

   # Create snapshot
   curl -X POST "http://localhost:8000/snapshot/create?description=Before refactoring"
   ```

2. **Make Changes**
   - Edit your Python code
   - Refactor functions, rename classes, etc.

3. **Re-index**
   ```bash
   curl -X POST http://localhost:8000/index -d '{"path": "./my_project"}'
   ```

4. **Create New Snapshot**
   ```bash
   curl -X POST "http://localhost:8000/snapshot/create?description=After refactoring"
   ```

5. **Compare**
   - Open frontend
   - Select both snapshots in history
   - Click "Compare" to see diff view
   - Green nodes = Added functions/classes
   - Red nodes = Deleted functions/classes
   - Orange nodes = Modified functions

6. **Validate**
   - Click "Validate" in header
   - Check for S/R/T law violations
   - Fix any issues

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Troubleshooting

### Backend won't start
- Check Neo4j is running: `http://localhost:7474`
- Verify credentials in backend/.env
- Check port 8000 is available

### Frontend won't connect
- Verify backend is running: `http://localhost:8000/health`
- Check CORS settings in backend/app/config.py
- Verify .env has correct API URL

### Graph not showing
- Check browser console for errors
- Verify data exists: `http://localhost:8000/stats`
- Try clearing browser cache

## Advanced Features

### Incremental Validation
Mark specific files as changed for faster validation:
```bash
curl -X POST http://localhost:8000/mark-changed \
  -d '{"files": ["path/to/file.py"]}'
```

### Pyright Integration
Enable deep type checking:
```bash
curl "http://localhost:8000/validate?pyright=true"
```

### Custom Queries
Use the query panel in the frontend for complex analysis:
- Find all callers of a function
- Trace type flow through functions
- Identify unused variables
- Map class hierarchies

## Next Steps

- Read the full theory in `docs/paper.tex`
- Explore the MCP server for LLM integration
- Check `backend/schema.md` for complete graph schema
- See `docs/THEORY_SUMMARY.md` for conservation laws

## Support

- Backend API: http://localhost:8000/docs
- Issues: https://github.com/yourusername/codegraph/issues
- Theory: See `docs/` directory
