# Git-Based Snapshot System Design

## Overview

Replace the manual snapshot system with automatic git-based snapshots. Each git commit represents a snapshot of the codebase graph.

## Current vs New System

### Current System (Manual)
- User manually creates snapshots
- Snapshots stored with custom IDs (hash of timestamp)
- No connection to version control
- Data stored in JSON files

### New System (Git-Based)
- Snapshots are automatic from git history
- Each commit hash = snapshot ID
- Tied to actual code versions
- Can view graph at any point in history

## Architecture

### Key Components

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Git Repo  │────▶│ GitSnapshotMgr   │────▶│   Neo4j     │
│  (History)  │     │ (Index on demand)│     │ (Current)   │
└─────────────┘     └──────────────────┘     └─────────────┘
                            │
                            ▼
                    ┌──────────────────┐
                    │ Snapshot Storage │
                    │  (JSON per commit)│
                    └──────────────────┘
```

### Data Flow

1. **List Commits**: `git log` → List of commits with metadata
2. **Index Commit**: Get files at commit → Parse → Build graph → Store snapshot
3. **View Commit**: Load snapshot JSON → Display in frontend
4. **Compare Commits**: Load two snapshots → Compute diff

## API Design

### Endpoints

```python
# List all commits (potential snapshots)
GET /commits
Response: [
  {
    "hash": "abc123",
    "short_hash": "abc123",
    "message": "Add feature X",
    "author": "John Doe",
    "date": "2024-01-15T10:30:00",
    "indexed": true  # Has been indexed
  }
]

# Get commit details
GET /commits/{hash}
Response: {
  "hash": "abc123",
  "message": "Add feature X",
  "author": "John Doe",
  "date": "2024-01-15T10:30:00",
  "files_changed": ["src/main.py", "src/utils.py"],
  "indexed": true
}

# Index a commit (build graph snapshot)
POST /commits/{hash}/index
Response: {
  "success": true,
  "stats": {
    "nodes": 150,
    "edges": 300
  }
}

# Get graph at commit
GET /commits/{hash}/graph
Response: {
  "nodes": [...],
  "edges": [...]
}

# Compare two commits
GET /commits/diff?old={hash1}&new={hash2}
Response: {
  "old_commit": "abc123",
  "new_commit": "def456",
  "summary": {...},
  "nodes": {
    "added": [...],
    "removed": [...],
    "modified": [...]
  },
  "edges": {...}
}
```

## Implementation

### GitSnapshotManager Class

```python
class GitSnapshotManager:
    def __init__(self, repo_path: str, storage_dir: str, db: CodeGraphDB):
        self.repo_path = repo_path
        self.storage_dir = storage_dir
        self.db = db
        self.parser = CodeGraphParser()

    def list_commits(self, limit: int = 50) -> List[CommitInfo]:
        """Get git commit history."""
        result = subprocess.run(
            ['git', 'log', f'--max-count={limit}',
             '--format=%H|%h|%s|%an|%aI'],
            cwd=self.repo_path,
            capture_output=True, text=True
        )
        # Parse and return commits

    def is_indexed(self, commit_hash: str) -> bool:
        """Check if commit has been indexed."""
        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")
        return os.path.exists(filepath)

    def index_commit(self, commit_hash: str) -> Dict:
        """Index code at specific commit."""
        # Get files at commit
        files = self._get_files_at_commit(commit_hash)

        # Parse each file
        for filepath, content in files.items():
            self.parser.parse_string(content, filepath)

        # Build graph
        entities, relationships = self.parser.get_results()

        # Store as snapshot
        snapshot = {
            "commit_hash": commit_hash,
            "timestamp": self._get_commit_date(commit_hash),
            "message": self._get_commit_message(commit_hash),
            "nodes": self._entities_to_nodes(entities),
            "edges": self._relationships_to_edges(relationships),
            "node_count": len(entities),
            "edge_count": len(relationships)
        }

        self._save_snapshot(commit_hash, snapshot)
        return snapshot

    def _get_files_at_commit(self, commit_hash: str) -> Dict[str, str]:
        """Get Python files at specific commit."""
        # List files at commit
        result = subprocess.run(
            ['git', 'ls-tree', '-r', '--name-only', commit_hash],
            cwd=self.repo_path,
            capture_output=True, text=True
        )

        files = {}
        for filepath in result.stdout.strip().split('\n'):
            if filepath.endswith('.py'):
                # Get file content at commit
                content = subprocess.run(
                    ['git', 'show', f'{commit_hash}:{filepath}'],
                    cwd=self.repo_path,
                    capture_output=True, text=True
                )
                files[filepath] = content.stdout

        return files

    def get_snapshot(self, commit_hash: str) -> Optional[Dict]:
        """Get snapshot for commit, indexing if needed."""
        if not self.is_indexed(commit_hash):
            self.index_commit(commit_hash)

        filepath = os.path.join(self.storage_dir, f"{commit_hash}.json")
        with open(filepath, 'r') as f:
            return json.load(f)

    def compare_commits(self, old_hash: str, new_hash: str) -> Dict:
        """Compare two commits."""
        old_snapshot = self.get_snapshot(old_hash)
        new_snapshot = self.get_snapshot(new_hash)

        # Reuse existing diff logic
        return self._compute_diff(old_snapshot, new_snapshot)
```

### Indexing Strategy

#### Option A: Index on Demand (Recommended)
- Only index commits when user selects them
- Lazy loading - don't index all history upfront
- Fast startup, minimal storage
- Trade-off: Slight delay on first view of a commit

#### Option B: Background Indexing
- Index recent commits automatically
- Background worker indexes historical commits
- Immediate access but high resource usage

#### Option C: Hybrid
- Auto-index HEAD and recent commits
- Index on demand for older commits

**Recommendation**: Option A (Index on Demand) for simplicity and efficiency.

### Storage Structure

```
snapshots/
  abc123def456.json     # Full commit hash
  fed987cba654.json
  ...
```

Each snapshot file:
```json
{
  "commit_hash": "abc123def456789...",
  "short_hash": "abc123d",
  "message": "Add feature X",
  "author": "John Doe",
  "date": "2024-01-15T10:30:00Z",
  "node_count": 150,
  "edge_count": 300,
  "nodes": [
    {
      "id": "...",
      "labels": ["Function"],
      "properties": {...}
    }
  ],
  "edges": [
    {
      "source": "...",
      "target": "...",
      "type": "CALLS",
      "properties": {}
    }
  ]
}
```

## Frontend Changes

### Snapshot List Component

Replace manual snapshot list with git commit history:

```typescript
interface CommitInfo {
  hash: string;
  shortHash: string;
  message: string;
  author: string;
  date: string;
  indexed: boolean;
}

// API calls
api.listCommits() -> CommitInfo[]
api.indexCommit(hash) -> void
api.getCommitGraph(hash) -> GraphData
api.compareCommits(oldHash, newHash) -> GraphDiff
```

### UI Changes

1. **Commit List**: Show git commits instead of manual snapshots
   - Commit message (truncated)
   - Author
   - Date
   - Indexed status (badge)

2. **Index Button**: Button to index unindexed commits
   - Loading state during indexing
   - Auto-refresh after indexing

3. **Comparison**: Select two commits to compare
   - Dropdown or click-to-select
   - Show diff visualization

### Example UI

```
┌─────────────────────────────────────────────────┐
│ Git History                            [Refresh]│
├─────────────────────────────────────────────────┤
│ ● abc123 - Add new calculator feature    [View] │
│   John Doe • 2 hours ago • Indexed              │
├─────────────────────────────────────────────────┤
│ ○ def456 - Fix divide by zero bug       [Index] │
│   Jane Smith • 1 day ago • Not indexed          │
├─────────────────────────────────────────────────┤
│ ● ghi789 - Initial commit                [View] │
│   John Doe • 3 days ago • Indexed               │
└─────────────────────────────────────────────────┘

[Compare Selected Commits]
```

## Edge Cases

### 1. File Not Found at Commit
Some files may not exist at older commits. Handle gracefully by skipping.

### 2. Parse Errors
Code at older commits may have syntax errors. Log and skip problematic files.

### 3. Large Repositories
For repos with many commits:
- Paginate commit list
- Limit to recent N commits by default
- Add date range filter

### 4. Binary Files
Skip non-Python files in indexing.

### 5. Deleted Files
When comparing, show files that were deleted as removed nodes.

## Migration

### From Old to New System

1. Keep old snapshots temporarily
2. Map old snapshots to nearest commit (by timestamp)
3. Eventually remove old manual snapshot code

### Backwards Compatibility

The `/snapshots` endpoints can remain but be deprecated:
- `/snapshots` → redirect to `/commits`
- `/snapshots/{id}` → map to commit hash if possible

## Performance Considerations

### Indexing Speed
- Parsing is the bottleneck
- Consider caching parsed ASTs
- Parallelize file parsing

### Storage Size
- Each snapshot is ~100KB-1MB depending on codebase
- 100 commits = ~100MB
- Consider compression for old snapshots

### Query Performance
- Loading snapshot JSON is fast
- Diff computation is O(n) where n = nodes + edges

## Security

### Git Operations
- Run git commands with restricted permissions
- Validate commit hashes (no command injection)
- Don't expose git credentials

### File Access
- Only parse Python files
- Validate file paths to prevent directory traversal

## Testing

### Unit Tests
- `test_list_commits` - Git log parsing
- `test_index_commit` - File extraction and parsing
- `test_compare_commits` - Diff computation

### Integration Tests
- Create test git repo with known history
- Index commits and verify graphs
- Compare commits and verify diffs

## Timeline

1. **Phase 1**: Core GitSnapshotManager (2-3 hours)
   - List commits
   - Index commit
   - Get snapshot

2. **Phase 2**: API endpoints (1-2 hours)
   - New routes for commits
   - Deprecate old snapshot routes

3. **Phase 3**: Frontend updates (2-3 hours)
   - Commit list component
   - Index button
   - Graph viewing

4. **Phase 4**: Comparison (1-2 hours)
   - Diff computation
   - Diff visualization

## Open Questions

1. **What directory to index?**
   - Entire repo?
   - Specific directories?
   - Configurable via API?

2. **Handle multiple Python projects in repo?**
   - Index all?
   - Let user select?

3. **Clean up old snapshots?**
   - Auto-delete after N days?
   - Limit to N snapshots?

4. **Branching?**
   - Show current branch only?
   - Allow switching branches?

## Conclusion

The git-based snapshot system provides:
- Automatic versioning tied to actual code changes
- Better UX (no manual snapshot creation)
- True code archaeology (view any point in history)
- Meaningful diffs (tied to commit messages)

Next step: Implement GitSnapshotManager class and API endpoints.
