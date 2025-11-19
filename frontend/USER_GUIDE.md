# CodeGraph Frontend - User Guide

## 🚀 Quick Start

```bash
# Start backend and Neo4j first
# Then:
cd frontend
npm install  # Already done!
npm run dev  # Start frontend
```

Open: **http://localhost:5173**

## 📊 Main Interface

The interface has 4 main areas:

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: [Graph] [Diff] [Validate] [Query]  [Actions]  │
├──────────┬────────────────────────────────┬─────────────┤
│          │                                │             │
│  LEFT    │        CENTER GRAPH            │    RIGHT    │
│  PANEL   │     (D3.js Visualization)      │   PANEL     │
│          │                                │             │
│ Snapshot │  • Drag nodes                  │  Inspector  │
│ History  │  • Zoom/Pan                    │             │
│ Timeline │  • Click to inspect            │  Shows:     │
│          │  • Labeled edges               │  - Node     │
│          │  • Force layout                │    details  │
│          │                                │  - Edge     │
│          │                                │    details  │
│          │                                │             │
├──────────┴────────────────────────────────┴─────────────┤
│                    BOTTOM PANEL                          │
│              Cypher Query Interface                      │
│     [Query Editor]  [Execute]  [Results Table]          │
└─────────────────────────────────────────────────────────┘
```

## 🎨 Graph Visualization (Center Panel)

### What You See

**Nodes** - Colored circles representing code elements:
- 🔵 **Blue** = Module
- 🟣 **Purple** = Class
- 🟢 **Green** = Function
- 🔷 **Teal** = Variable
- 🟡 **Yellow** = Parameter
- 🔴 **Red** = CallSite
- 🔴 **Pink** = Type
- 🟠 **Orange** = Decorator

**Edges** - Arrows showing relationships:
- Labels show relationship type (CALLS, CONTAINS, etc.)
- Different colors for different types
- Arrow points to target

### Interactions

| Action | Result |
|--------|--------|
| **Mouse Wheel** | Zoom in/out |
| **Click + Drag** (background) | Pan the graph |
| **Click + Drag** (node) | Move node to new position |
| **Click** (node) | Show details in right panel |
| **Click** (edge) | Show relationship details |
| **Hover** (node) | Node grows larger with shadow |
| **Hover** (edge) | Edge becomes thicker |

### Controls

**Top-Right Corner:**
- 🔍 **Reset Zoom** - Click to return to default view
- 🔄 **Re-layout** - Click to restart physics simulation

**Top-Left Corner:**
- **Legend** - Shows what each color means

**Bottom-Left Corner:**
- **Stats** - Node and edge counts

## 📁 Left Panel - Snapshot History

### What It Shows
- Timeline of all graph snapshots
- Like Git commits for your codebase
- Click any snapshot to view its graph

### How to Use

1. **Create Snapshot**
   - Click "Create Snapshot" in header
   - Enter description (optional)
   - Snapshot saved with timestamp

2. **View Snapshot**
   - Click any snapshot in list
   - Graph updates to show that state

3. **Compare Snapshots**
   - Select two snapshots
   - Click "Compare" button
   - Switches to Diff view

### Timeline Display
```
📅 2025-11-18 12:30 PM
   Initial codebase
   ├─ 25 nodes, 51 edges

📅 2025-11-18 01:45 PM
   After refactoring
   ├─ 28 nodes, 55 edges

📅 2025-11-18 02:15 PM
   Added new features
   ├─ 32 nodes, 63 edges
```

## 🔍 Right Panel - Inspector

### Node Details
When you click a node:
- **ID:** Unique identifier
- **Type:** Node type (Function, Class, etc.)
- **Name:** Element name
- **File Path:** Where it's defined
- **Line Number:** Exact location
- **Changed:** Whether it's been modified

### Function-Specific
- **Async:** Is it async?
- **Generator:** Is it a generator?
- **Return Type:** What it returns
- **Complexity:** Cyclomatic complexity

### Class-Specific
- **Abstract:** Is it abstract?
- **Base Classes:** What it inherits from

### Edge Details
When you click an edge:
- **Type:** Relationship type
- **From:** Source node
- **To:** Target node
- **Properties:** Additional metadata

## 💻 Bottom Panel - Cypher Query

### How to Query

1. **Type Query**
   ```cypher
   MATCH (n) RETURN n LIMIT 10
   ```

2. **Execute**
   - Click "Execute" button, or
   - Press **Ctrl+Enter** (Cmd+Enter on Mac)

3. **View Results**
   - Table shows all returned data
   - Each row is a result
   - Columns are return variables

### Query History
- Press **Ctrl+↑** - Previous query
- Press **Ctrl+↓** - Next query
- Stores last 50 queries

### Example Queries

**All Nodes:**
```cypher
MATCH (n) RETURN n LIMIT 100
```

**Changed Nodes:**
```cypher
MATCH (n) WHERE n.changed = true RETURN n
```

**Function Calls:**
```cypher
MATCH (f:Function)-[r:CALLS]->(g:Function)
RETURN f, r, g LIMIT 50
```

**Resolved Calls:**
```cypher
MATCH (c:CallSite)-[r:RESOLVES_TO]->(f:Function)
RETURN c, r, f
```

**Class Inheritance:**
```cypher
MATCH (c:Class)-[r:INHERITS]->(b:Class)
RETURN c, r, b
```

**Find Function by Name:**
```cypher
MATCH (f:Function)
WHERE f.name CONTAINS 'process'
RETURN f
```

## 🔀 Diff View

### How to Access
1. Select TWO snapshots in left panel
2. Click "Compare" in header
3. View switches to Diff mode

### View Modes

**Side-by-Side:**
- Left = Before (old snapshot)
- Right = After (new snapshot)
- See both states simultaneously

**Unified:**
- Single graph showing all changes
- Green = Added
- Red = Removed
- Orange = Modified

### Color Coding
- 🟢 **Green nodes/edges** = Added
- 🔴 **Red nodes/edges** = Removed (semi-transparent)
- 🟠 **Orange nodes** = Modified
- **Gray** = Unchanged

### Statistics Bar
Shows:
- X nodes added
- Y nodes removed
- Z nodes modified
- X edges added
- Y edges removed

## ✅ Validate View

### Conservation Laws

**S Law (Structural):**
- Graph structure valid?
- All edges follow schema?
- Node types correct?

**R Law (Referential):**
- All references resolve?
- No broken links?
- CallSites resolve to Functions?

**T Law (Typing):**
- Type annotations consistent?
- Function returns match?
- Variable types compatible?

### Violation Display

Click any law section to expand:
- Shows all violations
- File path and line number
- Error message
- Suggested fix

**Severity:**
- 🔴 **Error** - Must fix
- ⚠️ **Warning** - Should review

## 🎯 Common Workflows

### 1. Explore Codebase
```
1. Open frontend (graph view by default)
2. Zoom/pan to explore
3. Click nodes to see details
4. Follow edges to understand relationships
```

### 2. Track Changes
```
1. Create snapshot "Before refactoring"
2. Edit code in your IDE
3. Re-index: curl -X POST http://localhost:8000/index -d '{"path": "..."}'
4. Create snapshot "After refactoring"
5. Click both snapshots
6. Click "Compare"
7. See exactly what changed
```

### 3. Find Broken References
```
1. Click "Validate" in header
2. Expand "R Law" section
3. See all unresolved references
4. Click violation to see details
5. Fix in your IDE
6. Re-index and validate again
```

### 4. Analyze Function Calls
```
1. Click "Query" tab
2. Enter: MATCH (f:Function)-[r:CALLS]->(g:Function) RETURN f.name, g.name
3. Press Ctrl+Enter
4. See table of all function calls
```

### 5. Check Type Consistency
```
1. Click "Validate"
2. Expand "T Law" section
3. See type mismatches
4. Review and fix
```

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+Enter** | Execute query |
| **Ctrl+↑** | Previous query |
| **Ctrl+↓** | Next query |
| **Mouse Wheel** | Zoom graph |
| **Click+Drag** | Pan/move nodes |

## 🎨 Visual Design

### Colors Match Your Collatz Example
- Gradient backgrounds
- Drop shadows
- Smooth transitions
- Professional appearance
- Clean, modern interface

### Responsive
- Adapts to window size
- Panels can be resized
- Graph reflows on resize

## 🔧 Troubleshooting

### Graph Not Showing
1. Check backend is running: `http://localhost:8000/health`
2. Check data exists: `http://localhost:8000/stats`
3. Open browser console for errors

### Edges Have No Labels
- This should now be fixed!
- Labels show relationship types
- If not visible, try clicking "Re-layout"

### Graph Too Dense
1. Click "Reset Zoom"
2. Zoom out with mouse wheel
3. Or query for subset: `MATCH (n) RETURN n LIMIT 20`

### Slow Performance
- Limit nodes in query: `LIMIT 100`
- Use filters: `WHERE n.file_path = '...'`
- Close other browser tabs

## 📚 Learn More

- **Theory:** See `docs/paper.tex` for conservation laws
- **Schema:** See `backend/schema.md` for node/edge types
- **API:** See `http://localhost:8000/docs` for endpoints

## 💡 Tips

1. **Start small** - Query 10-20 nodes first
2. **Use snapshots** - Before every major change
3. **Validate often** - After each edit session
4. **Drag nodes** - Organize graph how you like
5. **Follow edges** - Trace code flow visually
6. **Compare snapshots** - See evolution over time

---

**Enjoy exploring your codebase as a living graph! 🚀**
