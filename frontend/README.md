# CodeGraph Frontend

A modern, interactive frontend for visualizing and analyzing CodeGraph data - better than Neo4j Browser.

## Features

- **Graph Visualization**: Interactive graph rendering with Cytoscape.js
- **Snapshot History**: Timeline view of graph snapshots (like VS Code history)
- **Diff View**: Side-by-side or unified comparison of snapshots with highlighted changes
- **Node/Edge Inspector**: Detailed property viewer for selected elements
- **Cypher Query Panel**: Execute custom queries with history
- **Validation View**: Conservation law (S, R, T) violation display
- **Change Highlighting**: Git-like visualization of added, removed, and modified nodes/edges

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and builds
- **TailwindCSS** for styling
- **Cytoscape.js** for graph visualization
- **Zustand** for state management
- **React Query** for data fetching

## Installation

```bash
cd frontend
npm install
```

## Configuration

Create a `.env` file:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Development

Start the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Build

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Usage

### 1. Start the Backend

Make sure the CodeGraph backend is running:

```bash
cd backend
python run.py
```

### 2. View the Graph

The main view shows the current graph state with:
- **Left Panel**: Snapshot history timeline
- **Center**: Interactive graph visualization
- **Right Panel**: Node/edge inspector
- **Bottom Panel**: Cypher query interface

### 3. Create Snapshots

Click "Create Snapshot" in the header to capture the current state.

### 4. Compare Snapshots

Select two snapshots from the history and click "Compare" to see changes:
- **Green**: Added nodes/edges
- **Red**: Removed nodes/edges
- **Orange**: Modified nodes

### 5. Validate

Click "Validate" to check conservation laws:
- **S Law**: Structural validity
- **R Law**: Referential coherence
- **T Law**: Semantic typing

### 6. Query

Use the bottom panel to execute Cypher queries:
- Use example queries as templates
- Press Ctrl+Enter to execute
- Use Ctrl+↑/↓ to navigate history

## Color Coding

### Node Types
- **Module**: Blue (#3498db)
- **Class**: Purple (#9b59b6)
- **Function**: Green (#2ecc71)
- **Variable**: Teal (#1abc9c)
- **Parameter**: Yellow (#f39c12)
- **CallSite**: Red (#e74c3c)
- **Type**: Pink (#e91e63)
- **Decorator**: Orange (#ff9800)

### Edge Types
- **RESOLVES_TO**: #4fc3f7
- **HAS_CALLSITE**: #27ae60
- **USES**: #3498db
- **DECLARES**: #9b59b6
- **INHERITS**: #e74c3c
- **DECORATES**: #f39c12
- **HAS_PARAMETER**: #16a085
- **RETURNS**: #2980b9
- **IS_SUBTYPE_OF**: #8e44ad

## License

MIT
