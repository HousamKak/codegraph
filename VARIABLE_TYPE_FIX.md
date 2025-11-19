# Variable Type Annotations Fix

## Issue

Variables in the frontend were not showing type borders even though:
1. The backend has code to create HAS_TYPE relationships for variables
2. The example code was updated with type annotations (`calc: Calculator`, `total: float`, etc.)

## Root Cause

The backend parser was **not capturing type annotations for local function variables**.

The parser only tracked type annotations for:
- ✅ Parameters (function arguments)
- ✅ Module-level variables
- ✅ Class-level variables
- ❌ **Local function variables** (MISSING)

## Code Analysis

### Where Variables Are Created

Local variables are created in `_get_or_create_local_variable()`:
```python
# backend/codegraph/parser.py:280
def _get_or_create_local_variable(self, name: str, func_id: str, file_path: str, node: ast.AST) -> str:
    var_entity = VariableEntity(
        id=var_id,
        name=name,
        location=self._get_location(node, file_path),
        node_type="Variable",
        scope="function"  # ⚠️ No type_annotation field!
    )
```

### Where Assignments Are Handled

Annotated assignments (`calc: Calculator = ...`) are processed in `_visit_statement()`:
```python
# backend/codegraph/parser.py:783-790
elif isinstance(node, ast.AnnAssign):
    if isinstance(node.target, ast.Name):
        self._handle_assignment_target(node.target, file_path, func_id)
        # ⚠️ Not passing node.annotation!
```

### Type Relationship Creation

The `_create_type_relationships()` function tries to link variables to types:
```python
# backend/codegraph/parser.py:1059-1070
if isinstance(entity, VariableEntity) and entity.type_annotation:
    var_type_id = self._get_or_create_type(
        entity.type_annotation,
        self.current_module
    )
    if var_type_id:
        self.relationships.append(Relationship(
            from_id=entity_id,
            to_id=var_type_id,
            rel_type="HAS_TYPE"
        ))
```

But this fails because `entity.type_annotation` is `None` for local variables!

## Fix Applied

### 1. Updated `_get_or_create_local_variable` (Line 280)

**Before:**
```python
def _get_or_create_local_variable(self, name: str, func_id: str, file_path: str, node: ast.AST) -> str:
    var_entity = VariableEntity(
        id=var_id,
        name=name,
        location=self._get_location(node, file_path),
        node_type="Variable",
        scope="function"
    )
```

**After:**
```python
def _get_or_create_local_variable(self, name: str, func_id: str, file_path: str, node: ast.AST, type_annotation: Optional[ast.AST] = None) -> str:
    var_entity = VariableEntity(
        id=var_id,
        name=name,
        location=self._get_location(node, file_path),
        node_type="Variable",
        type_annotation=self._get_type_annotation(type_annotation),  # ✅ Added
        scope="function"
    )
```

### 2. Updated `_handle_assignment_target` (Line 323)

**Before:**
```python
def _handle_assignment_target(self, target: ast.AST, file_path: str, func_id: str):
    if isinstance(target, ast.Name):
        var_id = self._get_or_create_local_variable(target.id, func_id, file_path, target)
```

**After:**
```python
def _handle_assignment_target(self, target: ast.AST, file_path: str, func_id: str, type_annotation: Optional[ast.AST] = None):
    if isinstance(target, ast.Name):
        var_id = self._get_or_create_local_variable(target.id, func_id, file_path, target, type_annotation)  # ✅ Pass annotation
```

### 3. Updated Call Site in `_visit_statement` (Line 786)

**Before:**
```python
elif isinstance(node, ast.AnnAssign):
    if isinstance(node.target, ast.Name):
        self._handle_assignment_target(node.target, file_path, func_id)
```

**After:**
```python
elif isinstance(node, ast.AnnAssign):
    if isinstance(node.target, ast.Name):
        self._handle_assignment_target(node.target, file_path, func_id, node.annotation)  # ✅ Pass annotation
```

## How to Apply the Fix

### Step 1: Restart the Backend

The backend needs to be restarted to reload the parser module with the changes:

**Option A: If running in terminal:**
1. Press `Ctrl+C` to stop the backend
2. Restart with: `cd backend && uvicorn codegraph.mcp_server:app --host 0.0.0.0 --port 8000 --reload`

**Option B: If running in Docker:**
```bash
docker-compose restart backend
```

### Step 2: Re-index the Code

After restarting the backend:
```bash
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" -d @reindex.json
```

### Step 3: Verify the Fix

Run the verification script:
```bash
python check_var_annotations.py
```

**Expected output:**
```
Variable details:
  calc: type_annotation=Calculator
  total: type_annotation=float
  calc: type_annotation=Calculator
  total: type_annotation=float
  results: type_annotation=dict[str, float]
  avg: type_annotation=float
```

### Step 4: Check Type Edges

```bash
python check_types.py
```

**Expected output should now include:**
```
Type edges by node type:
  Function: 7 edges
  Parameter: 12 edges
  Variable: 6 edges  ← NEW!
```

## Frontend Impact

Once the backend is fixed and re-indexed, variables with type annotations will:

1. **Show colored borders** in the graph visualization
2. **Display type labels** below nodes (`: Calculator`, `: float`)
3. **Not have HAS_TYPE arrow edges** (shown as borders instead)

### Example Visual

**Variable with type annotation:**
```
┌─────────────┐
│    calc     │  ← Cyan fill (Variable color)
│             │  ← Blue border (3px, type indicator)
└─────────────┘
 : Calculator   ← Blue type label
```

**Variable without type annotation:**
```
┌─────────────┐
│    item     │  ← Cyan fill (Variable color)
│             │  ← No border
└─────────────┘
```

## Files Modified

1. **backend/codegraph/parser.py**
   - Line 280: `_get_or_create_local_variable` - Added type_annotation parameter
   - Line 323: `_handle_assignment_target` - Added type_annotation parameter
   - Line 786: `_visit_statement` - Pass annotation from AnnAssign

2. **backend/examples/example_code.py**
   - Added type annotations to local variables:
     - Line 84: `calc: Calculator = Calculator()`
     - Line 85: `total: float = 0.0`
     - Line 107: `total: float = calculate_total(items)`
     - Line 108: `calc: Calculator = Calculator()`
     - Line 122: `results: dict[str, float] = {}`
     - Line 125: `avg: float = calculate_average(values)`

## Testing

After applying the fix and restarting:

### Test 1: Check Variable Properties
```python
# Should show type_annotation populated
import requests
r = requests.get('http://localhost:8000/graph?limit=100')
vars = [n for n in r.json()['nodes'] if 'Variable' in n['labels']]
for v in vars:
    print(v['properties']['name'], v['properties'].get('type_annotation'))
```

### Test 2: Count Type Edges
```python
r = requests.get('http://localhost:8000/graph?limit=100')
type_edges = [e for e in r.json()['edges'] if 'TYPE' in e['type']]
print(f'Total type edges: {len(type_edges)}')  # Should be 25+ (was 19)
```

### Test 3: Frontend Visualization
1. Open http://localhost:5173
2. Look for variable nodes (cyan color)
3. Variables with types should have blue borders
4. Type labels should appear below the nodes

## Troubleshooting

### Variables Still Don't Have Types

**Check 1:** Did you restart the backend?
```bash
# Verify the backend reloaded
curl http://localhost:8000/stats
```

**Check 2:** Did you re-index?
```bash
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" -d @reindex.json
```

**Check 3:** Does the source code have type annotations?
```python
# This will work:
total: float = 0.0

# This won't:
total = 0.0
```

### Backend Won't Start

Check for syntax errors:
```bash
cd backend
python -m py_compile codegraph/parser.py
```

### Still No Type Edges

Check Neo4j directly:
```cypher
MATCH (v:Variable)-[r:HAS_TYPE]->(t:Type)
RETURN v.name, t.name
LIMIT 10
```

If no results, the relationships weren't created. Check parser logs.

## Future Enhancements

1. **For loop variables**: Handle type hints for loop variables
   ```python
   for item: float in items:  # Type hint on loop var
       ...
   ```

2. **Walrus operator**: Handle annotated walrus assignments
   ```python
   if (result := calculate()) > 0:  # Could have type hint
       ...
   ```

3. **Multiple assignment**: Handle type hints for tuple unpacking
   ```python
   x: int, y: int = 1, 2
   ```

## Summary

The fix enables the backend to capture and store type annotations for local function variables, which then allows:
- The `_create_type_relationships()` function to create HAS_TYPE edges
- The frontend to display type borders and labels on variable nodes
- A cleaner graph with fewer arrow edges

**Next step:** Restart the backend and re-index!
