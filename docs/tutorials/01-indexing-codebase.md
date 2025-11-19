# Tutorial 1: Indexing Your First Codebase

## Introduction

In this tutorial, you'll learn how to index a Python codebase into CodeGraph's graph database. By the end, you'll understand how to:

- Start the CodeGraph backend
- Index Python files
- Verify the indexing worked
- Explore the resulting graph

**Time:** 15 minutes

**Prerequisites:**
- Docker installed
- Neo4j running
- CodeGraph backend set up

---

## Step 1: Start Neo4j

First, ensure Neo4j is running:

```bash
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

Wait 30 seconds for Neo4j to start, then verify:

```bash
curl http://localhost:7474
```

You should see the Neo4j browser interface.

---

## Step 2: Start CodeGraph Backend

Navigate to the backend directory and start the API:

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python run.py
```

You should see:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Test it's working:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "database_connected": true,
  "neo4j_uri": "bolt://localhost:7687"
}
```

---

## Step 3: Prepare Sample Code

Create a simple Python file to index:

```bash
mkdir -p ~/tutorial-project
cd ~/tutorial-project
```

Create `calculator.py`:
```python
"""Simple calculator module."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

def divide(a: int, b: int) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

Create `main.py`:
```python
"""Main application."""

from calculator import add, multiply

def calculate_total(items: list, tax_rate: float = 0.1) -> float:
    """Calculate total with tax."""
    subtotal = sum(items)
    tax = multiply(subtotal, tax_rate)
    total = add(subtotal, tax)
    return total

if __name__ == "__main__":
    items = [10, 20, 30]
    total = calculate_total(items)
    print(f"Total: ${total}")
```

---

## Step 4: Index the Codebase

Now index your project using the REST API:

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$HOME/tutorial-project\", \"clear\": true}"
```

**Expected response:**
```json
{
  "success": true,
  "message": "Indexed 6 entities",
  "data": {
    "entities_indexed": 6,
    "relationships_created": 8,
    "time_elapsed": "0.5s",
    "files_processed": 2
  }
}
```

**What happened:**
- CodeGraph parsed 2 Python files
- Extracted 5 functions + 1 module
- Created 8 relationships (DECLARES, HAS_PARAMETER, RESOLVES_TO)

---

## Step 5: Verify the Indexing

Check database statistics:

```bash
curl http://localhost:8000/stats
```

**Expected response:**
```json
{
  "stats": {
    "total_nodes": 18,
    "total_relationships": 24,
    "node_counts": {
      "Function": 5,
      "Module": 2,
      "Parameter": 11
    },
    "relationship_counts": {
      "DECLARES": 5,
      "HAS_PARAMETER": 11,
      "RESOLVES_TO": 3,
      "HAS_CALLSITE": 3,
      "IMPORTS": 2
    }
  }
}
```

**Understanding the counts:**
- **Functions:** 5 (add, subtract, multiply, divide, calculate_total)
- **Modules:** 2 (calculator.py, main.py)
- **Parameters:** 11 (2 per function except calculate_total which has 2)
- **RESOLVES_TO:** 3 (calculate_total calls add and multiply, main calls calculate_total)

---

## Step 6: Explore the Graph

### Find a Function

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"pattern": "calculate*", "entity_type": "Function"}'
```

**Response:**
```json
{
  "results": [
    {
      "id": "func_abc123",
      "type": "Function",
      "name": "calculate_total",
      "qualified_name": "main.calculate_total",
      "location": "main.py:5:0"
    }
  ],
  "total_results": 1
}
```

### Get Function Details

Use the ID from the previous response:

```bash
curl http://localhost:8000/functions/func_abc123
```

**Response:**
```json
{
  "function": {
    "id": "func_abc123",
    "name": "calculate_total",
    "qualified_name": "main.calculate_total",
    "signature": "calculate_total(items: list, tax_rate: float = 0.1) -> float",
    "location": "main.py:5:0",
    "docstring": "Calculate total with tax.",
    "parameters": [
      {
        "name": "items",
        "position": 0,
        "type_annotation": "list",
        "default_value": null
      },
      {
        "name": "tax_rate",
        "position": 1,
        "type_annotation": "float",
        "default_value": "0.1"
      }
    ],
    "return_type": "float"
  }
}
```

### Find Callers

```bash
curl http://localhost:8000/functions/func_add123/callers
```

This shows that `calculate_total` calls `add`.

---

## Step 7: Visualize in Neo4j Browser

Open http://localhost:7474 in your browser and run:

```cypher
MATCH (n) RETURN n LIMIT 50
```

You'll see:
- Blue nodes: Functions
- Green nodes: Parameters
- Orange nodes: Modules

Click nodes to see properties!

---

## Step 8: Re-index After Changes

Edit `main.py` to add a new function:

```python
def format_total(total: float) -> str:
    """Format total as currency."""
    return f"${total:.2f}"
```

Re-index (without clearing):

```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d "{\"path\": \"$HOME/tutorial-project/main.py\", \"clear\": false}"
```

**Note:** `clear: false` means incremental update - only changed file is re-parsed.

Verify the new function was added:

```bash
curl http://localhost:8000/stats
```

You should now have 6 functions instead of 5!

---

## Summary

You learned how to:

✅ Start Neo4j and CodeGraph backend
✅ Index a Python codebase
✅ Verify indexing with statistics
✅ Search for functions
✅ Get detailed function information
✅ Explore the graph visually
✅ Re-index after code changes

---

## Next Steps

- **Tutorial 2:** [Creating and Managing Snapshots](02-creating-snapshots.md)
- **Tutorial 3:** [Validating Code Changes](03-validating-changes.md)
- **Tutorial 4:** [Using MCP Tools with LLMs](04-using-mcp-tools.md)

---

## Troubleshooting

**Issue:** "Database connection failed"

**Solution:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Restart if needed
docker restart neo4j

# Wait 30 seconds
sleep 30
```

**Issue:** "Parsing error"

**Solution:**
- Ensure Python files are syntactically valid
- Check file encoding is UTF-8
- Review error details in response

**Issue:** "No entities indexed"

**Solution:**
- Verify path is correct
- Check files have .py extension
- Ensure path is absolute or relative to backend directory

---

**Last Updated:** 2025-01-19
