# CodeGraph Frontend - Comprehensive Analysis & Action Plan

## Executive Summary

**CodeGraph** is a "Software Physics" system that models codebases as semantic graphs governed by conservation laws (Structural, Referential, Typing). The frontend is a React + D3.js application that visualizes code relationships as interactive graphs.

Based on comprehensive exploration, I've identified the core issues and missing features:

## 1. Current State Analysis

### ✅ What's Working Well

1. **Graph Visualization** (`GraphView.tsx`)
   - D3.js force-directed layout rendering nodes (Functions, Classes, Modules, etc.) and edges (CALLS, INHERITS, etc.)
   - Pan/zoom, node selection, dragging
   - Type information displayed as outer rings on nodes
   - Edge filtering to prevent D3-force crashes (validNodeIds check)

2. **Structural Diff View** (`DiffView.tsx`)
   - Commit-to-commit comparison showing graph structural changes
   - Side-by-side and unified views
   - Color-coded nodes/edges (green=added, red=removed, orange=modified)
   - Summary statistics (nodes/edges added/removed/modified)

3. **File Explorer & Source Control**
   - File tree navigation with Python file highlighting
   - Git commit timeline with indexing status
   - Compare mode for selecting two commits

### ❌ Issues Identified

#### Issue 1: Unresolved Connections in Graph

**Root Cause**: The parser intentionally creates `Unresolved` nodes for references it cannot resolve (external imports like `numpy`, built-ins like `round()`, etc.). These are **by design** but not well-visualized.

**Evidence**:
- `/home/user/codegraph/backend/codegraph/parser.py:407-432` - Creates `UnresolvedReferenceEntity` nodes
- `/home/user/codegraph/backend/codegraph/builder.py:173-181` - Inserts Unresolved nodes into Neo4j
- `/home/user/codegraph/backend/codegraph/validators.py:544-572` - Validates and reports unresolved references as violations

**Frontend Impact**:
- Unresolved nodes ARE in the graph data but not visually distinguished
- No UI indication that certain connections are unresolved
- Users can't filter or highlight unresolved references
- Inspector panel doesn't show resolution status

**What's Missing**:
1. Visual indicator for unresolved nodes (different color, dashed border, icon)
2. Filter toggle to show/hide unresolved nodes
3. Inspector panel showing resolution status and reference kind
4. Count of unresolved references in graph stats
5. Clickable "resolve" action to investigate why a reference is unresolved

#### Issue 2: Git Diff Per File Not Working Fine

**Root Cause**: Current implementation only shows **graph structural diff** (nodes/edges changed) but NOT **text-based diff** (actual code line changes per file).

**Evidence**:
- `DiffView.tsx` only renders graph changes, no text diff
- Backend `/commits/diff` endpoint returns structural diff only
- No component for showing line-by-line code changes
- No integration with `git diff` output for text changes

**What's Missing**:
1. **Text-based diff view** component (like GitHub's diff view)
   - Side-by-side or unified text diff
   - Syntax highlighting for Python code
   - Line numbers with +/- indicators
   - Expandable context lines

2. **Per-file diff navigation**
   - List of changed files with stats (lines added/removed)
   - Click file to see its text diff
   - Navigate between files

3. **Integration between graph and text diffs**
   - Click modified node → jump to text diff for that function/class
   - Link from text diff line → highlight node in graph
   - Show which lines caused which graph changes

4. **Backend API support**
   - Endpoint to fetch text diff for specific file between commits
   - Parse `git diff` output and format for frontend
   - Map line changes to graph node changes

---

## 2. Detailed Action Plan

### Phase 1: Enhance Unresolved References Visualization

#### Task 1.1: Add Unresolved Node Visual Indicators

**Files to modify**:
- `frontend/src/components/GraphView.tsx:202-207` - Add conditional styling for Unresolved nodes
- `frontend/src/types/index.ts` - Add `Unresolved` to NODE_COLORS

**Changes**:
```typescript
// In GraphView.tsx - node circle rendering
node.append('circle')
  .attr('r', (d: any) => d.labels[0] === 'Unresolved' ? 14 : 18)  // Smaller for unresolved
  .attr('fill', (d: any) => {
    if (d.labels[0] === 'Unresolved') return '#ef4444';  // Red for unresolved
    return NODE_COLORS[d.labels[0]] || '#93c5fd';
  })
  .attr('stroke-dasharray', (d: any) => d.labels[0] === 'Unresolved' ? '4,4' : 'none')  // Dashed border
  .attr('opacity', (d: any) => d.labels[0] === 'Unresolved' ? 0.6 : 1);
```

#### Task 1.2: Add Filter Toggle for Unresolved Nodes

**Files to create/modify**:
- `frontend/src/components/GraphView.tsx` - Add filter state and controls

**Changes**:
```typescript
const [showUnresolved, setShowUnresolved] = useState(true);

// Filter nodes based on toggle
const filteredNodes = graphData.nodes.filter(node =>
  showUnresolved || node.labels[0] !== 'Unresolved'
);

// Add UI toggle in header
<button onClick={() => setShowUnresolved(!showUnresolved)}>
  {showUnresolved ? 'Hide' : 'Show'} Unresolved ({unresolvedCount})
</button>
```

#### Task 1.3: Enhance Inspector Panel for Unresolved Nodes

**Files to modify**:
- `frontend/src/components/RightPanel.tsx` - Add Unresolved node properties display

**Changes**:
- Show resolution status
- Display reference kind (call, import, variable)
- Show source entity that created the unresolved reference
- Suggest possible resolutions (install package, fix typo, etc.)

#### Task 1.4: Add Unresolved Reference Statistics

**Files to modify**:
- `frontend/src/components/Header.tsx` or create `GraphStats.tsx`

**Changes**:
- Show total unresolved references count
- Group by type (external imports, built-ins, unknown)
- Click to filter graph to show only unresolved

---

### Phase 2: Implement Per-File Text Diff Functionality

#### Task 2.1: Create Backend API for Text Diffs

**Files to create/modify**:
- `backend/app/routers/commits.py` - Add new endpoint

**New endpoint**:
```python
@router.get("/commits/diff/file")
async def get_file_diff(
    old: str,
    new: str,
    filepath: str
) -> FileDiff:
    """Get text diff for a specific file between two commits."""
    git_mgr = get_git_manager()
    diff = git_mgr.get_file_diff(old, new, filepath)
    return diff
```

**Files to modify**:
- `backend/codegraph/git_snapshot.py` - Add `get_file_diff()` method

**Implementation**:
```python
def get_file_diff(self, old_hash: str, new_hash: str, filepath: str) -> Dict:
    """Get text diff for a file using git diff."""
    cmd = ["git", "diff", f"{old_hash}..{new_hash}", "--", filepath]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.repo_root)

    # Parse unified diff format
    lines = result.stdout.split('\n')
    hunks = self._parse_diff_hunks(lines)

    return {
        "filepath": filepath,
        "old_hash": old_hash,
        "new_hash": new_hash,
        "hunks": hunks,
        "stats": self._calculate_diff_stats(hunks)
    }
```

#### Task 2.2: Create File List with Diff Stats Component

**Files to create**:
- `frontend/src/components/FileChangesPanel.tsx`

**Features**:
- List all files changed between two commits
- Show lines added/removed per file
- Icons for file type (added, modified, deleted)
- Click file to view its text diff
- Search/filter files
- Group by directory

#### Task 2.3: Create Text Diff Viewer Component

**Files to create**:
- `frontend/src/components/TextDiffView.tsx`

**Features**:
- Side-by-side or unified diff view (like GitHub)
- Syntax highlighting using `react-syntax-highlighter`
- Line numbers with +/- indicators
- Expandable context lines
- Jump to line functionality
- Copy code button

**Libraries to add**:
```json
{
  "react-syntax-highlighter": "^15.5.0",
  "react-diff-view": "^3.0.0"
}
```

**Implementation approach**:
```typescript
import { Diff, Hunk, parseDiff } from 'react-diff-view';
import 'react-diff-view/style/index.css';

export const TextDiffView: React.FC<{ filepath: string }> = ({ filepath }) => {
  const { diffData } = useStore();
  const [diffText, setDiffText] = useState('');

  useEffect(() => {
    // Fetch text diff from API
    api.getFileDiff(diffData.old_commit, diffData.new_commit, filepath)
      .then(data => setDiffText(data.unified_diff));
  }, [filepath]);

  const files = parseDiff(diffText);

  return (
    <div>
      {files.map(file => (
        <Diff key={file.oldPath} viewType="split" diffType={file.type}>
          {file.hunks.map(hunk => (
            <Hunk key={hunk.content} hunk={hunk} />
          ))}
        </Diff>
      ))}
    </div>
  );
};
```

#### Task 2.4: Integrate Text Diff with Graph View

**Files to modify**:
- `frontend/src/components/DiffView.tsx` - Add split pane with text diff
- `frontend/src/App.tsx` - Add new route/view for combined diff

**Changes**:
- Add tabs: "Graph Diff" | "Text Diff" | "Combined"
- In "Combined" view:
  - Left: Graph visualization
  - Right: Text diff for selected file/node
- Click modified node in graph → show text diff for containing file, scrolled to function
- Click line in text diff → highlight corresponding node in graph

#### Task 2.5: Add File-Level Navigation

**Files to create**:
- `frontend/src/components/DiffNavigator.tsx`

**Features**:
- Sidebar with file tree of changed files
- Each file shows +/- line count
- Click to view text diff
- Keyboard shortcuts (J/K to navigate files)
- Progress indicator (3/15 files reviewed)

---

### Phase 3: Advanced Features (Nice to Have)

#### Task 3.1: Inline Comments/Annotations

**Features**:
- Add comments to specific lines in diff
- Annotations for unresolved references
- Link comments to graph nodes

#### Task 3.2: Diff History Timeline

**Features**:
- Timeline slider to see evolution across multiple commits
- Animated transitions between commits
- Heatmap of files by change frequency

#### Task 3.3: Smart Diff Filtering

**Features**:
- Filter diffs by:
  - Only breaking changes (S/R/T violations)
  - Only API changes (public function signatures)
  - Only test changes
  - By file pattern (src/* vs tests/*)

#### Task 3.4: AI-Powered Diff Summary

**Features**:
- LLM-generated summary of changes
- Impact analysis (what breaks downstream)
- Suggested review focus areas

---

## 3. Implementation Priority

### High Priority (Do First)

1. **Unresolved node visualization** (Task 1.1) - Low effort, high impact
2. **Backend text diff API** (Task 2.1) - Foundation for text diff
3. **Text diff viewer component** (Task 2.3) - Core missing functionality
4. **File changes list** (Task 2.2) - Navigation for text diffs

### Medium Priority (Do Next)

5. **Filter toggle for unresolved** (Task 1.2) - Improves graph clarity
6. **Unresolved inspector details** (Task 1.3) - Better debugging
7. **Integration graph + text diff** (Task 2.4) - Powerful combined view

### Low Priority (Nice to Have)

8. **Unresolved statistics** (Task 1.4) - Metrics/monitoring
9. **Diff navigator** (Task 2.5) - UX improvement
10. **Advanced features** (Phase 3) - Future enhancements

---

## 4. Technical Specifications

### New Backend API Endpoints

```python
# Get text diff for specific file
GET /commits/diff/file?old={hash}&new={hash}&filepath={path}
Response: { filepath, old_hash, new_hash, hunks, stats }

# Get list of changed files
GET /commits/diff/files?old={hash}&new={hash}
Response: [{ filepath, status, lines_added, lines_removed, hunks_count }]

# Get file content at commit
GET /commits/{hash}/file?filepath={path}
Response: { filepath, content, encoding }
```

### New Frontend Components

```
frontend/src/components/
├── TextDiffView.tsx          # Main text diff viewer
├── FileChangesPanel.tsx      # List of changed files
├── DiffNavigator.tsx         # Navigation sidebar
├── UnresolvedFilter.tsx      # Unresolved nodes filter
└── CombinedDiffView.tsx      # Graph + Text integrated view
```

### New State Management

```typescript
// Add to store/index.ts
interface DiffState {
  // Existing
  diffData: CommitDiff | null;
  compareFromGraph: GraphData | null;
  compareToGraph: GraphData | null;

  // New
  selectedFileDiff: FileDiff | null;  // Current file's text diff
  changedFiles: FileChange[];         // List of all changed files
  selectedFileForDiff: string | null; // Currently viewing file
  diffViewMode: 'graph' | 'text' | 'combined';  // View mode
  showUnresolved: boolean;            // Filter unresolved nodes
}
```

### Dependencies to Add

```json
{
  "dependencies": {
    "react-diff-view": "^3.0.0",
    "react-syntax-highlighter": "^15.5.0",
    "diff": "^5.1.0",
    "unidiff": "^1.0.4"
  }
}
```

---

## 5. Testing Strategy

### Unit Tests

- Parse git diff output correctly
- Filter unresolved nodes from graph
- Calculate diff statistics accurately
- Handle binary files, large diffs, empty diffs

### Integration Tests

- Fetch file diff from backend
- Display text diff with syntax highlighting
- Navigate between files in diff
- Link graph nodes to text lines

### E2E Tests

- User selects two commits
- Views graph diff
- Switches to text diff
- Clicks modified node → sees text diff
- Filters unresolved nodes
- Navigates through changed files

---

## 6. Documentation Needs

### User Guide Updates

- How to interpret unresolved connections
- How to view text diffs per file
- How to navigate between graph and text views
- Keyboard shortcuts for diff navigation

### Developer Documentation

- Backend git diff implementation
- Frontend diff view architecture
- State management for diff data
- How to extend with new diff features

---

## 7. Estimated Effort

| Phase | Tasks | Effort | Dependencies |
|-------|-------|--------|--------------|
| Phase 1 (Unresolved) | 4 tasks | 2-3 days | None |
| Phase 2 (Text Diff) | 5 tasks | 5-7 days | Phase 1 complete |
| Phase 3 (Advanced) | 4 tasks | 4-5 days | Phase 2 complete |
| **Total** | **13 tasks** | **11-15 days** | Sequential |

---

## 8. Risks & Mitigations

### Risk 1: Large Diffs Performance
- **Mitigation**: Virtualize long diffs, lazy load hunks

### Risk 2: Complex Git History
- **Mitigation**: Handle merge commits, handle binary files gracefully

### Risk 3: State Management Complexity
- **Mitigation**: Use React Query for caching, normalize state shape

---

## 9. Success Metrics

### Functionality
- ✅ Unresolved nodes visually distinguished in graph
- ✅ Can toggle visibility of unresolved nodes
- ✅ Text diff displays for any file between commits
- ✅ Can navigate from graph node to text diff
- ✅ Can navigate between changed files

### Performance
- ✅ Text diff loads in <500ms
- ✅ Graph filtering updates in <100ms
- ✅ Smooth scrolling in diff view

### UX
- ✅ Intuitive navigation between views
- ✅ Clear visual indicators
- ✅ Helpful error messages

---

## 10. Quick Reference: Key Findings

### Unresolved Connections Issue
**Status**: NOT A BUG - By design
- Parser creates `Unresolved` nodes for external/built-in references
- These nodes exist in graph but lack visual distinction
- **Solution**: Add visual indicators, filters, and better documentation

### Git Diff Issue
**Status**: MISSING FEATURE
- Current diff view only shows structural changes (graph nodes/edges)
- No text-based line-by-line diff view
- **Solution**: Implement full text diff functionality with GitHub-like UI

### Backend Health
- ✅ Neo4j graph database working
- ✅ Git snapshot system functional
- ✅ Parser creates correct unresolved nodes
- ✅ Validators detect unresolved references
- ⚠️ Missing text diff endpoints

### Frontend Health
- ✅ D3.js graph rendering working
- ✅ Structural diff view working
- ✅ Edge filtering prevents crashes
- ⚠️ Unresolved nodes not visually distinguished
- ❌ Text diff view completely missing
