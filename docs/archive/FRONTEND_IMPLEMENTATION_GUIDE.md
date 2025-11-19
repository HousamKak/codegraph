# Frontend Implementation Guide - Text Diff Components

## Progress Summary

### ✅ Phase 1 Complete: Unresolved Node Visualization

All tasks completed and committed:
- Added visual indicators (red color, dashed border, smaller size, 70% opacity)
- Implemented filter toggle to show/hide unresolved nodes
- Enhanced inspector panel with UnresolvedProperties component
- Display count of unresolved nodes in UI

### ✅ Phase 2 Partial: Text Diff Backend

Completed and committed:
- Backend API methods in `git_snapshot.py`:
  - `get_file_diff(old_hash, new_hash, filepath)`
  - `list_changed_files(old_hash, new_hash)`
- API endpoints in `commits.py`:
  - `GET /commits/diff/file`
  - `GET /commits/diff/files`
- Frontend API client methods in `client.ts`:
  - `getFileDiff(oldHash, newHash, filepath)`
  - `listChangedFiles(oldHash, newHash)`

### 🚧 Phase 2 Remaining: Frontend Text Diff Components

These components still need to be implemented:

---

## Task 1: Install Frontend Dependencies

### Commands to Run

```bash
cd frontend
npm install react-diff-view@3.0.0 diff@5.1.0
```

### Dependencies Needed

```json
{
  "react-diff-view": "^3.0.0",
  "diff": "^5.1.0"
}
```

**Note**: `react-syntax-highlighter` is already installed (check package.json).

---

## Task 2: Add Type Definitions

### File: `frontend/src/types/index.ts`

Add these new type definitions:

```typescript
// File diff types
export interface FileDiff {
  filepath: string;
  old_hash: string;
  new_hash: string;
  diff: string;
  lines_added: number;
  lines_removed: number;
  is_binary: boolean;
}

export interface FileChange {
  filepath: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed' | 'copied';
  lines_added: number;
  lines_removed: number;
  is_binary: boolean;
}
```

---

## Task 3: Update Store State

### File: `frontend/src/store/index.ts`

Add these state properties and setters:

```typescript
interface State {
  // ... existing state ...

  // New text diff state
  selectedFileDiff: FileDiff | null;
  changedFiles: FileChange[];
  selectedFileForDiff: string | null;
  diffViewMode: 'graph' | 'text' | 'combined';
  showUnresolved: boolean;  // Already added to GraphView, add to global store

  // Setters
  setSelectedFileDiff: (diff: FileDiff | null) => void;
  setChangedFiles: (files: FileChange[]) => void;
  setSelectedFileForDiff: (filepath: string | null) => void;
  setDiffViewMode: (mode: 'graph' | 'text' | 'combined') => void;
  setShowUnresolved: (show: boolean) => void;
}

// Implementation in create<State>((set) => ({ ... }))
const useStore = create<State>((set) => ({
  // ... existing state ...

  selectedFileDiff: null,
  changedFiles: [],
  selectedFileForDiff: null,
  diffViewMode: 'graph',
  showUnresolved: true,

  setSelectedFileDiff: (diff) => set({ selectedFileDiff: diff }),
  setChangedFiles: (files) => set({ changedFiles: files }),
  setSelectedFileForDiff: (filepath) => set({ selectedFileForDiff: filepath }),
  setDiffViewMode: (mode) => set({ diffViewMode: mode }),
  setShowUnresolved: (show) => set({ showUnresolved: show }),
}));
```

---

## Task 4: Create FileChangesPanel Component

### File: `frontend/src/components/FileChangesPanel.tsx`

This component shows a list of changed files with stats.

```typescript
import React, { useEffect } from 'react';
import { useStore } from '../store';
import { api } from '../api/client';
import { File, FileX, FilePlus, FileEdit } from 'lucide-react';

export const FileChangesPanel: React.FC = () => {
  const compareFrom = useStore((state) => state.compareFrom);
  const compareTo = useStore((state) => state.compareTo);
  const changedFiles = useStore((state) => state.changedFiles);
  const selectedFileForDiff = useStore((state) => state.selectedFileForDiff);
  const setChangedFiles = useStore((state) => state.setChangedFiles);
  const setSelectedFileForDiff = useStore((state) => state.setSelectedFileForDiff);
  const setError = useStore((state) => state.setError);

  useEffect(() => {
    if (compareFrom && compareTo) {
      fetchChangedFiles();
    }
  }, [compareFrom, compareTo]);

  const fetchChangedFiles = async () => {
    if (!compareFrom || !compareTo) return;

    try {
      const result = await api.listChangedFiles(compareFrom, compareTo);
      setChangedFiles(result.files);
    } catch (error) {
      setError(`Failed to load changed files: ${(error as Error).message}`);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'added':
        return <FilePlus size={16} className="text-green-500" />;
      case 'deleted':
        return <FileX size={16} className="text-red-500" />;
      case 'modified':
        return <FileEdit size={16} className="text-yellow-500" />;
      default:
        return <File size={16} className="text-gray-500" />;
    }
  };

  if (!compareFrom || !compareTo) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        Select two commits to view changed files
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border p-3 bg-panel-bg">
        <h3 className="text-sm font-semibold">Changed Files ({changedFiles.length})</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        {changedFiles.length === 0 ? (
          <div className="p-4 text-center text-text-secondary">
            No files changed
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {changedFiles.map((file) => (
              <li
                key={file.filepath}
                className={`p-3 hover:bg-hover cursor-pointer transition-colors ${
                  selectedFileForDiff === file.filepath ? 'bg-accent/10' : ''
                }`}
                onClick={() => setSelectedFileForDiff(file.filepath)}
              >
                <div className="flex items-start gap-2">
                  {getStatusIcon(file.status)}
                  <div className="flex-1 min-w-0">
                    <div className="font-mono text-sm truncate" title={file.filepath}>
                      {file.filepath}
                    </div>
                    <div className="flex gap-3 mt-1 text-xs text-text-secondary">
                      <span className="text-green-600">
                        +{file.lines_added}
                      </span>
                      <span className="text-red-600">
                        -{file.lines_removed}
                      </span>
                      {file.is_binary && (
                        <span className="text-gray-500">(binary)</span>
                      )}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
```

---

## Task 5: Create TextDiffView Component

### File: `frontend/src/components/TextDiffView.tsx`

This component displays the text diff using react-diff-view.

```typescript
import React, { useEffect, useState } from 'react';
import { parseDiff, Diff, Hunk } from 'react-diff-view';
import { useStore } from '../store';
import { api } from '../api/client';
import 'react-diff-view/style/index.css';

export const TextDiffView: React.FC = () => {
  const compareFrom = useStore((state) => state.compareFrom);
  const compareTo = useStore((state) => state.compareTo);
  const selectedFileForDiff = useStore((state) => state.selectedFileForDiff);
  const selectedFileDiff = useStore((state) => state.selectedFileDiff);
  const setSelectedFileDiff = useStore((state) => state.setSelectedFileDiff);
  const setError = useStore((state) => state.setError);

  const [viewType, setViewType] = useState<'split' | 'unified'>('split');

  useEffect(() => {
    if (compareFrom && compareTo && selectedFileForDiff) {
      fetchFileDiff();
    }
  }, [compareFrom, compareTo, selectedFileForDiff]);

  const fetchFileDiff = async () => {
    if (!compareFrom || !compareTo || !selectedFileForDiff) return;

    try {
      const diff = await api.getFileDiff(compareFrom, compareTo, selectedFileForDiff);
      setSelectedFileDiff(diff);
    } catch (error) {
      setError(`Failed to load diff: ${(error as Error).message}`);
    }
  };

  if (!selectedFileForDiff) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        Select a file to view its diff
      </div>
    );
  }

  if (!selectedFileDiff) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        Loading diff...
      </div>
    );
  }

  if (selectedFileDiff.is_binary) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        <div className="text-center">
          <p>Binary file - no text diff available</p>
          <p className="text-xs mt-2">{selectedFileDiff.filepath}</p>
        </div>
      </div>
    );
  }

  if (!selectedFileDiff.diff) {
    return (
      <div className="h-full flex items-center justify-center text-text-secondary">
        No changes in this file
      </div>
    );
  }

  const files = parseDiff(selectedFileDiff.diff);

  return (
    <div className="h-full flex flex-col bg-white">
      <div className="border-b border-border p-3 bg-panel-bg flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold font-mono">{selectedFileDiff.filepath}</h3>
          <div className="flex gap-3 mt-1 text-xs text-text-secondary">
            <span className="text-green-600">+{selectedFileDiff.lines_added}</span>
            <span className="text-red-600">-{selectedFileDiff.lines_removed}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setViewType('split')}
            className={`px-3 py-1 rounded text-sm ${
              viewType === 'split'
                ? 'bg-accent text-white'
                : 'bg-panel-bg text-text-secondary hover:text-text-primary'
            }`}
          >
            Split
          </button>
          <button
            onClick={() => setViewType('unified')}
            className={`px-3 py-1 rounded text-sm ${
              viewType === 'unified'
                ? 'bg-accent text-white'
                : 'bg-panel-bg text-text-secondary hover:text-text-primary'
            }`}
          >
            Unified
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {files.map((file, index) => (
          <Diff key={index} viewType={viewType} diffType={file.type} hunks={file.hunks}>
            {(hunks) =>
              hunks.map((hunk) => <Hunk key={hunk.content} hunk={hunk} />)
            }
          </Diff>
        ))}
      </div>
    </div>
  );
};
```

---

## Task 6: Update DiffView Component

### File: `frontend/src/components/DiffView.tsx`

Add tabs to switch between graph diff and text diff:

```typescript
// At the top of the component
const [activeTab, setActiveTab] = useState<'graph' | 'text'>('graph');

// Add tab navigation before the existing content
<div className="border-b border-border bg-panel-bg">
  <div className="flex gap-4 px-4">
    <button
      onClick={() => setActiveTab('graph')}
      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        activeTab === 'graph'
          ? 'border-accent text-accent'
          : 'border-transparent text-text-secondary hover:text-text-primary'
      }`}
    >
      Graph Diff
    </button>
    <button
      onClick={() => setActiveTab('text')}
      className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        activeTab === 'text'
          ? 'border-accent text-accent'
          : 'border-transparent text-text-secondary hover:text-text-primary'
      }`}
    >
      Text Diff
    </button>
  </div>
</div>

// Replace the main content area with conditional rendering
{activeTab === 'graph' && (
  // ... existing graph diff content ...
)}

{activeTab === 'text' && (
  <div className="flex h-full">
    <div className="w-80 border-r border-border">
      <FileChangesPanel />
    </div>
    <div className="flex-1">
      <TextDiffView />
    </div>
  </div>
)}
```

---

## Task 7: Test the Implementation

### Testing Checklist

1. **Backend API Testing:**
   ```bash
   # Start backend
   cd backend
   python -m uvicorn app.main:app --reload

   # Test endpoints (replace hashes with actual commits)
   curl "http://localhost:8000/commits/diff/files?old=HASH1&new=HASH2"
   curl "http://localhost:8000/commits/diff/file?old=HASH1&new=HASH2&filepath=path/to/file.py"
   ```

2. **Frontend Testing:**
   ```bash
   # Start frontend
   cd frontend
   npm run dev

   # Open http://localhost:5173
   # 1. Navigate to Source Control panel
   # 2. Select two commits for comparison
   # 3. Click "Graph Diff" tab - should show structural changes
   # 4. Click "Text Diff" tab - should show file list and text diffs
   # 5. Click on files to view their diffs
   # 6. Toggle between Split and Unified views
   ```

3. **Unresolved Nodes Testing:**
   - Load a file with external imports (e.g., `import numpy`)
   - Verify unresolved nodes appear in red with dashed borders
   - Click unresolved filter button - nodes should disappear
   - Click again - nodes should reappear
   - Select an unresolved node - inspector should show UnresolvedProperties

---

## Task 8: Optional Enhancements

### Enhancement 1: Syntax Highlighting in Diff

Install and configure:
```bash
npm install prism-react-renderer
```

Integrate with react-diff-view for syntax highlighting.

### Enhancement 2: Link Graph Nodes to Text Diff

When user clicks a modified node in graph, automatically:
1. Switch to "Text Diff" tab
2. Select the file containing that node
3. Scroll to the line number of the node

### Enhancement 3: Keyboard Shortcuts

Add shortcuts for navigation:
- `j`/`k`: Next/previous file
- `[`/`]`: Next/previous hunk
- `t`: Toggle split/unified view

---

## Summary

### Completed (7 tasks):
1. ✅ Unresolved node visualization
2. ✅ Filter toggle for unresolved nodes
3. ✅ Inspector panel for unresolved nodes
4. ✅ Backend API for file diffs
5. ✅ Backend API for changed files list
6. ✅ Frontend API client methods
7. ✅ Documentation and plan

### Remaining (5 tasks):
1. ⏳ Install frontend dependencies
2. ⏳ Add type definitions
3. ⏳ Create FileChangesPanel component
4. ⏳ Create TextDiffView component
5. ⏳ Update DiffView component with tabs

### Estimated Time:
- Remaining tasks: 2-3 hours
- Testing and refinement: 1-2 hours
- **Total: 3-5 hours**

---

## Quick Start Commands

```bash
# Install dependencies
cd frontend && npm install react-diff-view diff

# Run development
cd frontend && npm run dev

# In another terminal, run backend
cd backend && python -m uvicorn app.main:app --reload

# Access at http://localhost:5173
```
