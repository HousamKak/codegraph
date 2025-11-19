# Tutorial 3: Validating Code Changes

## Introduction

Conservation law validation ensures your code maintains integrity across changes. Learn to:

- Validate 4 conservation laws
- Fix signature mismatches
- Handle reference errors
- Use validation in LLM workflows

**Time:** 25 minutes

---

## The 4 Conservation Laws

1. **Signature Conservation**: Function signatures match call sites
2. **Reference Integrity**: All references resolve
3. **Data Flow Consistency**: Type annotations consistent
4. **Structural Integrity**: Graph structure valid

---

## Step 1: Create Invalid Code

Create `~/tutorial-project/broken.py`:

```python
def process_data(data: list) -> dict:
    """Process data and return results."""
    validated = validate_data(data)  # Function doesn't exist!
    total = calculate_total(validated)  # Wrong number of args!
    return {"total": total}

def calculate_total(items: list, discount: bool) -> float:
    """Calculate total."""
    # Now requires 2 args, but called with 1
    return sum(items) * (0.9 if discount else 1.0)
```

Index it:
```bash
curl -X POST http://localhost:8000/index \
  -d '{"path": "/home/user/tutorial-project/broken.py", "clear": false}'
```

---

## Step 2: Run Validation

```bash
curl "http://localhost:8000/validate"
```

**Response:**
```json
{
  "valid": false,
  "violations": [
    {
      "law": "Reference Integrity",
      "type": "reference_broken",
      "severity": "error",
      "message": "Call to undefined function 'validate_data'",
      "file_path": "broken.py",
      "line_number": 3,
      "column_number": 17,
      "code_snippet": "    validated = validate_data(data)",
      "suggested_fix": "Define validate_data or import it"
    },
    {
      "law": "Signature Conservation",
      "type": "signature_mismatch",
      "severity": "error",
      "message": "Function calculate_total expects 2 arguments but called with 1",
      "file_path": "broken.py",
      "line_number": 4,
      "column_number": 12,
      "code_snippet": "    total = calculate_total(validated)",
      "suggested_fix": "Add missing argument: calculate_total(validated, False)"
    }
  ],
  "summary": {
    "signature_conservation": 1,
    "reference_integrity": 1,
    "data_flow_consistency": 0,
    "structural_integrity": 0
  },
  "total_violations": 2
}
```

---

## Step 3: Fix Violations

Fix broken.py:

```python
def validate_data(data: list) -> list:
    """Validate data."""
    return [x for x in data if x is not None]

def process_data(data: list) -> dict:
    """Process data and return results."""
    validated = validate_data(data)  # ✅ Now defined
    total = calculate_total(validated, False)  # ✅ Correct args
    return {"total": total}

def calculate_total(items: list, discount: bool) -> float:
    """Calculate total."""
    return sum(items) * (0.9 if discount else 1.0)
```

Re-index and validate:

```bash
curl -X POST http://localhost:8000/index \
  -d '{"path": "/home/user/tutorial-project/broken.py", "clear": false}'

curl "http://localhost:8000/validate"
```

**Response:**
```json
{
  "valid": true,
  "violations": [],
  "summary": {
    "signature_conservation": 0,
    "reference_integrity": 0,
    "data_flow_consistency": 0,
    "structural_integrity": 0
  },
  "total_violations": 0
}
```

✅ All violations fixed!

---

## Step 4: Deep Type Checking with Pyright

For stricter validation, enable pyright:

```bash
curl "http://localhost:8000/validate?include_pyright=true"
```

This runs the pyright type checker for deeper analysis.

---

## Step 5: LLM Workflow Example

Simulating an LLM editing code:

**1. Create snapshot before:**
```bash
curl -X POST "http://localhost:8000/snapshot/create?description=Before%20LLM%20edit"
```

**2. LLM adds parameter to function:**
```python
# Was: def calculate_total(items: list, discount: bool) -> float:
# Now: def calculate_total(items: list, discount: bool, tax_rate: float) -> float:
def calculate_total(items: list, discount: bool, tax_rate: float) -> float:
    """Calculate total with tax."""
    subtotal = sum(items) * (0.9 if discount else 1.0)
    tax = subtotal * tax_rate
    return subtotal + tax
```

**3. Re-index:**
```bash
curl -X POST http://localhost:8000/index \
  -d '{"path": "/home/user/tutorial-project/broken.py", "clear": false}'
```

**4. Validate - Will show violations:**
```bash
curl "http://localhost:8000/validate"
```

```json
{
  "violations": [
    {
      "law": "Signature Conservation",
      "message": "Function calculate_total expects 3 arguments but called with 2",
      "file_path": "broken.py",
      "line_number": 8,
      "suggested_fix": "Update call site: calculate_total(validated, False, 0.1)"
    }
  ]
}
```

**5. LLM fixes all call sites:**
```python
total = calculate_total(validated, False, 0.1)
```

**6. Validate again - Clean:**
```bash
curl "http://localhost:8000/validate"
# {"valid": true, "violations": []}
```

**7. Create snapshot after:**
```bash
curl -X POST "http://localhost:8000/snapshot/create?description=After%20LLM%20edit%20-%20all%20fixed"
```

---

## Step 6: Incremental Validation

For large codebases, validate only changed files:

```bash
# Mark specific files as changed
curl -X POST http://localhost:8000/mark-changed \
  -d '{"files": ["broken.py"]}'

# Validate only changed nodes
curl "http://localhost:8000/validate?changed_only=true"
```

This is much faster!

---

## Summary

You learned:

✅ The 4 conservation laws
✅ How to run validation
✅ How to interpret violation reports
✅ How to fix violations
✅ LLM workflow with validation
✅ Incremental validation

---

## Next Steps

- **Tutorial 4:** [Using MCP Tools with LLMs](04-using-mcp-tools.md)
- **Guide:** [API Reference](../guides/API_REFERENCE.md)

---

**Last Updated:** 2025-01-19
