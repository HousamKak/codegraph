# Example: Complete LLM Workflow with CodeGraph

This example shows a complete workflow where an LLM uses CodeGraph to safely refactor code.

## Scenario

User asks: "Add a discount parameter to calculate_total and update all callers"

## Complete Workflow

### Step 1: Initial Analysis

**LLM Query:**
```
find_function(name="calculate_total")
```

**Result:**
```json
{
  "id": "func_calc123",
  "name": "calculate_total",
  "signature": "calculate_total(items: list, tax_rate: float = 0.1) -> float"
}
```

### Step 2: Impact Analysis

**LLM Query:**
```
get_function_callers(function_id="func_calc123")
```

**Result:**
```json
{
  "callers": [
    {"name": "process_order", "location": "orders.py:35"},
    {"name": "generate_invoice", "location": "invoices.py:42"}
  ]
}
```

### Step 3: Create Snapshot

**LLM Query:**
```
create_snapshot(description="Before adding discount parameter")
```

**Result:**
```json
{
  "snapshot_id": "snap_abc123",
  "timestamp": "2025-01-19T14:00:00Z"
}
```

### Step 4: Edit Function

**LLM Action:** Use Edit tool

```python
# Before
def calculate_total(items: list, tax_rate: float = 0.1) -> float:
    subtotal = sum(item.price for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax

# After
def calculate_total(items: list, discount: float = 0.0, tax_rate: float = 0.1) -> float:
    subtotal = sum(item.price for item in items)
    discounted = subtotal * (1 - discount)
    tax = discounted * tax_rate
    return discounted + tax
```

### Step 5: Re-index

**LLM Query:**
```
index_codebase(path="/project/billing.py", clear=false)
```

### Step 6: Validate

**LLM Query:**
```
validate_codebase()
```

**Result:**
```json
{
  "valid": false,
  "violations": [
    {
      "message": "Function calculate_total signature changed but callers unchanged",
      "location": "orders.py:35",
      "suggested_fix": "Add discount argument"
    },
    {
      "message": "Function calculate_total signature changed but callers unchanged",
      "location": "invoices.py:42",
      "suggested_fix": "Add discount argument"
    }
  ]
}
```

### Step 7: Fix Callers

**LLM Action:** Edit both call sites

```python
# orders.py - Before
total = calculate_total(items, 0.08)

# After
total = calculate_total(items, 0.0, 0.08)  # No discount, 8% tax

# invoices.py - Before
total = calculate_total(cart_items)

# After
total = calculate_total(cart_items, 0.15, 0.1)  # 15% discount, 10% tax
```

### Step 8: Re-index and Re-validate

**LLM Query:**
```
index_codebase(path="/project", clear=false)
validate_codebase()
```

**Result:**
```json
{
  "valid": true,
  "violations": []
}
```

### Step 9: Final Snapshot

**LLM Query:**
```
create_snapshot(description="After adding discount parameter - all callers updated")
```

### Step 10: Compare Results

**LLM Query:**
```
compare_snapshots(
  old_snapshot_id="snap_abc123",
  new_snapshot_id="snap_def456"
)
```

**Result:**
```json
{
  "nodes_modified": 1,
  "edges_modified": 2,
  "summary": "Function signature updated, all 2 callers updated successfully"
}
```

## Outcome

✅ Function parameter added
✅ All callers updated
✅ Zero violations
✅ Complete audit trail (snapshots)
✅ Total time: 2 minutes

## Without CodeGraph

The LLM would likely:
- Update the function ✅
- Miss one caller ❌
- Error discovered at runtime ❌
- Require multiple iterations ❌
- No audit trail ❌

---

**Last Updated:** 2025-01-19
