# Neo4j Schema for Python Code Graph

This document describes the actual graph that CodeGraph now produces when indexing a Python project. It is the canonical reference for all node/relationship types exposed through MCP, REST, and Cypher queries.

## Recent Schema Optimizations (2025)

**Removed Redundancies:**
- ❌ **CONTAINS** - Removed (was created but never queried; redundant with DECLARES)
- ❌ **CALLS** - Merged into RESOLVES_TO (eliminated duplicate edges)
- ❌ **DEFINES** - Renamed to DECLARES for theory alignment

**Current Minimal Schema:**
- 14 relationship types (down from 19)
- ~30-40% reduction in edge count
- Full alignment with S/R/T conservation laws
- Import cycle detection added to R law validation

## Node Types

### Function
```
Properties:
- id: unique identifier
- name: simple name
- qualified_name: module.class.function
- signature: canonical signature string
- return_type: raw annotation (string)
- visibility: public/private
- is_async / is_generator / is_staticmethod / is_classmethod / is_property: booleans
- location: file:line:column
- docstring: optional string
- decorators: list of decorator names
```

### Class
```
Properties:
- id, name, qualified_name, visibility, location
- docstring: documentation string
- bases: list of base class names
- decorators: list of decorator names
```

### Variable
```
Properties:
- id: unique identifier (module/class/function scoped)
- name: symbol name
- scope: module/class/function
- type_annotation: annotation string (optional)
- location: first seen definition
```

### Parameter
```
Properties:
- id, name, location
- type_annotation: optional
- position: integer (order)
- default_value: string representation (optional)
- kind: positional/keyword/var_positional/var_keyword
```

### Module
```
Properties:
- id: unique identifier
- name: module stem
- qualified_name: dotted module path
- path: filesystem-like path (dotted imports become /)
- package: package name (if any)
- location: definition or import site
- docstring: optional
- is_external: true when generated from an import placeholder
```

### CallSite
```
Properties:
- id: unique identifier per caller+callee+location
- name: human readable label (call_{callee}@line)
- caller_id: id of calling function
- arg_count: positional argument count
- has_args / has_kwargs: bool flags for *args/**kwargs
- lineno / col_offset / location: where the call happens
```

### Type
```
Properties:
- id: unique identifier
- name: canonical type string
- module: module namespace (builtins, typing, etc.)
- kind: class/generic/union
- location: module or builtins
- base_types: list of parent types (for builtin hierarchy)
```

### Decorator
```
Properties:
- id: unique identifier per target+decorator
- name: decorator expression string
- target_id: id of the class/function being decorated
- target_type: "Class" or "Function"
- location: decorator location
```

## Relationship Types

### DECLARES
```
From: Module | Class
To: Class | Function | Variable
Purpose: Declarations at module and class level
Note: Unified relationship for both module-level and class-level declarations (methods)
```

### HAS_PARAMETER
```
From: Function
To: Parameter
Properties:
- position: parameter order
```

### RESOLVES_TO
```
From: CallSite
To: Function
Properties:
- resolution_status: "resolved" or "unresolved"
- callee_name: textual target name
Purpose: Unified call tracking with resolution status for R law validation
Note: Replaces the old CALLS relationship to avoid redundancy
```

### HAS_CALLSITE
```
From: Function
To: CallSite
Purpose: enumerate every place this function calls something else
```

### INHERITS
```
From: Class
To: Class
Properties:
- base_name: textual parent reference
```

### IMPORTS
```
From: Module
To: Module (placeholder nodes created for import targets)
Properties:
- import_name: raw symbol imported
- from_module: module path for `from ... import ...`
- alias: alias used in code (optional)
```

### RETURNS_TYPE
```
From: Function
To: Type
Purpose: capture return annotations
```

### HAS_TYPE
```
From: Parameter/Variable
To: Type
Purpose: capture annotations for inputs and state
```

### IS_SUBTYPE_OF
```
From: Type
To: Type
Purpose: builtin + inferred subtype hierarchy
```

### ASSIGNS_TO
```
From: Function
To: Variable
Properties:
- location: write site
Purpose: records where functions assign to scope-local/module/class variables
```

### READS_FROM
```
From: Function
To: Variable
Properties:
- location: read site
Purpose: records variable usage for data-flow analysis
```

### REFERENCES
```
From: Function/Class/Decorator
To: Variable/Function/Class/Decorator/Type
Properties:
- access_type: read/write/call
- location: usage site
Purpose: generic cross-entity reference tracking used by validators
```

### HAS_DECORATOR
```
From: Function/Class
To: Decorator
Purpose: attach decorator nodes to their target
```

### DECORATES
```
From: Decorator
To: Function/Class
Purpose: inverse link for navigation + validator support
```

## Indexes & Constraints

Created via `CodeGraphDB.initialize_schema`:
```cypher
CREATE CONSTRAINT function_id_unique IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT module_id_unique IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT variable_id_unique IF NOT EXISTS FOR (v:Variable) REQUIRE v.id IS UNIQUE;
CREATE CONSTRAINT parameter_id_unique IF NOT EXISTS FOR (p:Parameter) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT type_id_unique IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE;

CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name);
CREATE INDEX function_qualified_idx IF NOT EXISTS FOR (f:Function) ON (f.qualified_name);
CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name);
CREATE INDEX variable_name_idx IF NOT EXISTS FOR (v:Variable) ON (v.name);
CREATE INDEX module_path_idx IF NOT EXISTS FOR (m:Module) ON (m.path);
```

## Incremental Validation Support

Nodes can have a `changed` property to support incremental validation:
```
n.changed = true  // Node was modified and needs validation
n.snapshot_id = "abc123"  // Snapshot this node belongs to
```

### Propagation
When nodes are marked as changed, the change propagates along dependency edges:
- Functions that call changed functions
- Classes that inherit from changed classes
- Parameters of changed functions
- Modules that import changed modules

This enables efficient local-to-global validation per the theory's Soundness Theorem.

## Conservation Law Coverage

### S Law (Structural Validity)
- Edge type validation ensures edges connect correct node types
- `HAS_PARAMETER` position uniqueness
- `INHERITS` acyclicity detection
- Parameter ownership (exactly one function per parameter)

### R Law (Referential Coherence)
- `RESOLVES_TO` ensures each CallSite resolves to exactly one Function with resolution status
- `REFERENCES` and `IMPORTS` ensure references resolve
- `IMPORTS` cycle detection prevents circular module dependencies
- Unresolved calls are tracked via `resolution_status` property

### T Law (Semantic Typing Correctness)
- `HAS_TYPE`, `RETURNS_TYPE`, `IS_SUBTYPE_OF` for type tracking
- Pyright integration for deep type checking
- Variable read/write edges for data flow analysis

### Original Four Laws Mapping
1. **Signature Conservation** → T + S
2. **Reference Integrity** → R
3. **Data Flow Consistency** → T
4. **Graph Structural Integrity** → S + R
