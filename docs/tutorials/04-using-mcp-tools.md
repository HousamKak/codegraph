# Tutorial 4: Using MCP Tools with LLMs

## Introduction

The MCP (Model Context Protocol) server provides 13 tools for LLMs to analyze code. Learn to:

- Configure MCP server with Claude
- Use tools for code analysis
- Complete LLM-driven refactoring
- Validate changes automatically

**Time:** 30 minutes

**Prerequisites:**
- Claude Code or compatible LLM client
- CodeGraph backend running

---

## Step 1: Configure MCP Server

Add to your Claude Code configuration (typically `~/.claude/config.json`):

```json
{
  "mcpServers": {
    "codegraph": {
      "command": "python",
      "args": ["/path/to/codegraph/backend/codegraph/mcp_server.py"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password"
      }
    }
  }
}
```

Restart Claude Code to load the MCP server.

---

## Step 2: Verify MCP Tools Available

In Claude Code, ask:

> "What CodeGraph tools do you have access to?"

Claude should list all 13 tools:

1. index_codebase
2. get_graph_stats
3. find_function
4. get_function_details
5. get_function_callers
6. get_function_callees
7. get_function_dependencies
8. search_code
9. analyze_impact
10. validate_codebase
11. create_snapshot
12. compare_snapshots
13. list_snapshots

---

## Step 3: Index Codebase via MCP

Ask Claude:

> "Please index the codebase at /home/user/tutorial-project"

Claude will use the `index_codebase` tool:

```json
{
  "path": "/home/user/tutorial-project",
  "clear": false
}
```

Result: "Successfully indexed 6 functions across 3 files."

---

## Step 4: Explore with MCP Tools

Ask Claude to explore:

> "What functions are in this codebase?"

Claude uses `search_code`:
```json
{
  "pattern": "*",
  "entity_type": "Function"
}
```

Claude responds:
"I found these functions:
- add (calculator.py)
- subtract (calculator.py)
- multiply (calculator.py)
- divide (calculator.py)
- calculate_total (main.py)
- power (calculator.py)"

---

## Step 5: Get Function Details

Ask:

> "Show me details about the calculate_total function"

Claude uses `find_function` then `get_function_details`:

Response:
```
calculate_total is defined in main.py at line 5.

Signature: calculate_total(items: list, tax_rate: float = 0.1) -> float

Parameters:
- items (list): required
- tax_rate (float): optional, default=0.1

Returns: float

Docstring: "Calculate total with tax."
```

---

## Step 6: Impact Analysis

Ask:

> "What would break if I delete the multiply function?"

Claude uses `analyze_impact`:
```json
{
  "entity_id": "func_multiply_id",
  "change_type": "delete"
}
```

Claude reports:
"Deleting multiply would affect:
- calculate_total (main.py:7) calls it
- calculate_compound (main.py:15) calls it

Recommendation: Update 2 callers before deletion."

---

## Step 7: Complete Refactoring Workflow

**Scenario**: Add a discount parameter to calculate_total.

**User:**
> "Add a required discount parameter to calculate_total and update all callers."

**Claude's workflow:**

1. **Create snapshot:**
```json
{"description": "Before adding discount parameter"}
```

2. **Find function:**
```json
{"name": "calculate_total"}
```

3. **Analyze impact:**
```json
{"entity_id": "func_calc_total", "change_type": "modify"}
```

Claude reports: "1 caller found in main.py"

4. **Edit code** (using Edit tool):
```python
def calculate_total(items: list, discount: float, tax_rate: float = 0.1) -> float:
    """Calculate total with discount and tax."""
    subtotal = sum(items) * (1 - discount)
    tax = subtotal * tax_rate
    return subtotal + tax
```

5. **Update caller:**
```python
total = calculate_total(items, 0.0)  # No discount
```

6. **Re-index:**
```json
{"path": "/home/user/tutorial-project/main.py"}
```

7. **Validate:**
```json
{"include_pyright": false}
```

Result: "✅ Validation passed! No violations found."

8. **Create final snapshot:**
```json
{"description": "After adding discount parameter"}
```

---

## Step 8: Validation-Driven Development

**User:**
> "Rename add to sum_values and update all references."

**Claude's careful approach:**

1. **Find all callers first:**
```json
{"function_id": "func_add_id"}
```

Result: "2 callers: calculate_total, another_function"

2. **Create snapshot**

3. **Rename function**

4. **Update all 2 callers**

5. **Re-index**

6. **Validate:**
```json
{"include_pyright": true}
```

If violations found, Claude fixes them before proceeding.

7. **Final snapshot**

---

## Step 9: Compare Workflow Results

**User:**
> "Show me what changed during the refactoring."

**Claude:**
```json
{
  "old_snapshot_id": "snap_before",
  "new_snapshot_id": "snap_after"
}
```

Result:
```
Changes detected:
- Modified: 1 function (signature changed)
- Modified: 2 call sites (argument added)
- Modified: 1 module (imports unchanged)

Total: 4 entities modified, 0 added, 0 deleted
```

---

## Step 10: Best Practices

### Always Create Snapshots

Before major changes:
```
User: "Refactor the authentication module"
Claude: 
1. create_snapshot("Before auth refactoring")
2. [perform refactoring]
3. validate_codebase()
4. create_snapshot("After auth refactoring")
```

### Validate Incrementally

After each file edit:
```
1. Edit file
2. index_codebase(specific_file)
3. validate_codebase()
4. If violations: fix and repeat
```

### Use Impact Analysis

Before deletions:
```
1. analyze_impact(entity_id, "delete")
2. Review affected code
3. Update or refactor callers first
4. Then delete
```

---

## Example Conversation

**User:**
> "I want to add error handling to the divide function. Make sure it won't break anything."

**Claude:**
```
I'll help you add error handling safely. Let me first check what calls the divide function.

[Uses get_function_callers]

The divide function is not currently called by any other code in this codebase, so we can safely modify it without affecting other code.

[Creates snapshot: "Before adding error handling to divide"]

[Edits divide function to add try/except]

[Re-indexes the file]

[Validates]

✅ Validation passed! The error handling has been added and won't break any existing code.

[Creates snapshot: "After adding error handling to divide"]

Would you like me to add tests for the error cases?
```

---

## Summary

You learned:

✅ Configure MCP server
✅ Use 13 MCP tools via LLM
✅ Complete end-to-end refactoring
✅ Validation-driven development
✅ Best practices for safe code changes

---

## Advanced Topics

- [MCP Server Architecture](../architecture/MCP_SERVER.md)
- [API Reference](../guides/API_REFERENCE.md)
- [Developer Guide](../guides/DEVELOPER_GUIDE.md)

---

**Last Updated:** 2025-01-19
