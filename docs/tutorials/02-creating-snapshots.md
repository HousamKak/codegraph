# Tutorial 2: Creating and Managing Snapshots

## Introduction

Snapshots capture the state of your codebase at a specific point in time. They're essential for:

- Tracking code evolution
- Comparing before/after changes
- Rolling back if needed
- Audit trails

**Time:** 20 minutes

**Prerequisites:**
- Completed Tutorial 1
- Codebase already indexed

---

## Step 1: Understanding Snapshots

A snapshot is a frozen copy of your graph at a moment in time. It includes:
- All nodes (functions, classes, modules, etc.)
- All relationships
- Metadata (timestamp, description, tags)

Snapshots enable "time travel" - you can compare any two points in your codebase history.

---

## Step 2: Create Your First Snapshot

Create a baseline snapshot:

```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Initial%20state"
```

**Response:**
```json
{
  "snapshot_id": "snap_20250119_140000",
  "description": "Initial state",
  "timestamp": "2025-01-19T14:00:00Z",
  "stats": {
    "total_nodes": 18,
    "total_edges": 24
  }
}
```

**Save the snapshot_id** - you'll need it later!

---

## Step 3: Make Code Changes

Now let's modify the code and create another snapshot.

Edit `~/tutorial-project/calculator.py`, add a new function:

```python
def power(base: int, exponent: int) -> int:
    """Raise base to exponent."""
    return base ** exponent
```

Edit `~/tutorial-project/main.py`, use the new function:

```python
from calculator import add, multiply, power

def calculate_compound(principal: float, rate: float, years: int) -> float:
    """Calculate compound interest."""
    multiplier = power(1 + rate, years)
    return multiply(principal, multiplier)
```

---

## Step 4: Re-index and Create New Snapshot

Re-index the modified files:

```bash
curl -X POST http://localhost:8000/index \
  -d '{"path": "/home/user/tutorial-project", "clear": false}'
```

Create a new snapshot:

```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Added%20power%20function&tags=feature,math"
```

**Response:**
```json
{
  "snapshot_id": "snap_20250119_141500",
  "description": "Added power function",
  "timestamp": "2025-01-19T14:15:00Z",
  "tags": ["feature", "math"],
  "stats": {
    "total_nodes": 24,
    "total_edges": 32
  }
}
```

---

## Step 5: Compare Snapshots

Now compare the two snapshots to see what changed:

```bash
curl -X POST "http://localhost:8000/snapshot/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "old_snapshot_id": "snap_20250119_140000",
    "new_snapshot_id": "snap_20250119_141500"
  }'
```

**Response:**
```json
{
  "comparison": {
    "nodes_added": [
      {
        "id": "func_power_123",
        "type": "Function",
        "name": "power",
        "location": "calculator.py:20:0"
      },
      {
        "id": "func_compound_456",
        "type": "Function",
        "name": "calculate_compound",
        "location": "main.py:15:0"
      }
    ],
    "nodes_removed": [],
    "nodes_modified": [
      {
        "id": "mod_main",
        "type": "Module",
        "name": "main",
        "changes": {
          "imports": {
            "added": ["power"]
          }
        }
      }
    ],
    "edges_added": 8,
    "edges_removed": 0
  },
  "summary": {
    "total_changes": 11,
    "nodes_changed": 3,
    "edges_changed": 8
  }
}
```

**Analysis:**
- 2 new functions added (power, calculate_compound)
- Module modified (new import)
- 8 new relationships (parameters, calls, etc.)
- No deletions

---

## Step 6: List All Snapshots

```bash
curl http://localhost:8000/snapshot/list
```

**Response:**
```json
{
  "snapshots": [
    {
      "snapshot_id": "snap_20250119_141500",
      "description": "Added power function",
      "timestamp": "2025-01-19T14:15:00Z",
      "tags": ["feature", "math"]
    },
    {
      "snapshot_id": "snap_20250119_140000",
      "description": "Initial state",
      "timestamp": "2025-01-19T14:00:00Z",
      "tags": []
    }
  ],
  "total": 2
}
```

Snapshots are listed newest first.

---

## Step 7: Refactoring Workflow

Let's do a refactoring and track it with snapshots.

**Before refactoring:**
```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Before%20renaming%20functions&tags=refactoring"
```

**Refactor:** Rename `calculate_total` to `compute_total_with_tax`

Edit `main.py`:
```python
def compute_total_with_tax(items: list, tax_rate: float = 0.1) -> float:
    """Calculate total with tax."""
    # ... same implementation ...
```

**After refactoring:**
```bash
# Re-index
curl -X POST http://localhost:8000/index \
  -d '{"path": "/home/user/tutorial-project/main.py", "clear": false}'

# Create snapshot
curl -X POST "http://localhost:8000/snapshot/create?description=Renamed%20calculate_total&tags=refactoring"
```

**Compare:**
```bash
curl -X POST "http://localhost:8000/snapshot/compare" \
  -d '{
    "old_snapshot_id": "snap_before_id",
    "new_snapshot_id": "snap_after_id"
  }'
```

You'll see:
- 1 node removed (old function)
- 1 node added (new function)
- Call sites updated

---

## Step 8: Using Snapshots for Code Review

Create snapshots before and after a pull request:

```bash
# Baseline
git checkout main
curl -X POST http://localhost:8000/index -d '{"path": ".", "clear": true}'
curl -X POST "http://localhost:8000/snapshot/create?description=Main%20branch&tags=baseline"

# Feature branch
git checkout feature/new-feature
curl -X POST http://localhost:8000/index -d '{"path": ".", "clear": true}'
curl -X POST "http://localhost:8000/snapshot/create?description=Feature%20branch&tags=feature"

# Compare
curl -X POST "http://localhost:8000/snapshot/compare" \
  -d '{"old_snapshot_id": "main_snap", "new_snapshot_id": "feature_snap"}'
```

This shows exactly what the PR changes!

---

## Step 9: Best Practices

### Naming Conventions

Use descriptive names:
```bash
# Good
"description=Before%20refactoring%20auth%20module"
"description=After%20adding%20caching%20layer"
"description=Baseline%20for%20v2.0%20release"

# Bad
"description=Test"
"description=Snapshot%201"
```

### Tagging Strategy

Use tags for categorization:
```bash
"tags=refactoring"
"tags=feature,authentication"
"tags=bugfix,critical"
"tags=release,v1.0"
```

### Cleanup Old Snapshots

Snapshots are currently in-memory. For production:
- Implement persistence
- Archive old snapshots
- Keep only last N snapshots
- Or keep snapshots for releases only

---

## Summary

You learned how to:

✅ Create snapshots of graph state
✅ Compare snapshots to see changes
✅ List all snapshots
✅ Use snapshots in refactoring workflows
✅ Best practices for naming and tagging

---

## Next Steps

- **Tutorial 3:** [Validating Code Changes](03-validating-changes.md)
- **Tutorial 4:** [Using MCP Tools with LLMs](04-using-mcp-tools.md)

---

## Exercise

Try this yourself:

1. Create a snapshot
2. Delete a function from your code
3. Re-index
4. Create new snapshot
5. Compare snapshots

What do you see in `nodes_removed`?

---

**Last Updated:** 2025-01-19
