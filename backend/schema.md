# Neo4j Schema for Python Code Graph

## Node Types

### Function
```
Properties:
- id: unique identifier
- name: function name
- qualified_name: full path (module.class.function)
- signature: string representation
- return_type: type annotation (optional)
- visibility: public/private (_prefix)
- is_async: boolean
- location: file:line:column
- docstring: documentation
```

### Class
```
Properties:
- id: unique identifier
- name: class name
- qualified_name: full path
- visibility: public/private
- location: file:line:column
- docstring: documentation
- is_abstract: boolean
```

### Variable
```
Properties:
- id: unique identifier
- name: variable name
- type_annotation: type hint (optional)
- scope: local/global/nonlocal/class
- location: file:line:column
```

### Parameter
```
Properties:
- id: unique identifier
- name: parameter name
- type_annotation: type hint (optional)
- position: integer
- default_value: string representation (optional)
- kind: positional/keyword/var_positional/var_keyword
- location: file:line:column
```

### Module
```
Properties:
- id: unique identifier
- path: file path
- name: module name
- package: package name (optional)
```

### Type
```
Properties:
- id: unique identifier
- name: type name (int, str, List[int], etc.)
- is_builtin: boolean
```

## Relationship Types

### CALLS
```
From: Function/Method
To: Function/Method
Properties:
- arg_count: number of arguments
- location: where the call happens
- is_valid: boolean (for validation)
```

### DEFINES
```
From: Module/Class/Function
To: Function/Class/Variable
Properties:
- location: where defined
```

### REFERENCES
```
From: Function/Class
To: Variable/Function/Class
Properties:
- access_type: read/write/call
- location: where referenced
```

### HAS_PARAMETER
```
From: Function
To: Parameter
Properties:
- position: integer (for ordering)
```

### RETURNS
```
From: Function
To: Type
Properties:
- is_annotated: boolean (explicit vs inferred)
```

### INHERITS
```
From: Class
To: Class
Properties:
- position: integer (for multiple inheritance)
```

### IMPORTS
```
From: Module
To: Module/Function/Class
Properties:
- alias: import alias (optional)
- is_from_import: boolean
```

### TYPED_AS
```
From: Variable/Parameter
To: Type
Properties:
- is_annotated: boolean
```

### CONTAINS
```
From: Module/Class
To: Class/Function/Variable
Properties:
- scope: enclosing scope info
```

### ASSIGNS_TO
```
From: Function/Method
To: Variable
Properties:
- location: assignment location
```

### READS_FROM
```
From: Function/Method
To: Variable
Properties:
- location: read location
```

## Indexes

```cypher
CREATE INDEX function_name_idx FOR (f:Function) ON (f.name);
CREATE INDEX function_qualified_idx FOR (f:Function) ON (f.qualified_name);
CREATE INDEX class_name_idx FOR (c:Class) ON (c.name);
CREATE INDEX variable_name_idx FOR (v:Variable) ON (v.name);
CREATE INDEX module_path_idx FOR (m:Module) ON (m.path);
CREATE CONSTRAINT function_id_unique FOR (f:Function) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT class_id_unique FOR (c:Class) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT module_id_unique FOR (m:Module) REQUIRE m.id IS UNIQUE;
```

## Conservation Law Mappings

### 1. Signature Conservation
- Query all CALLS relationships to a Function
- Compare arg_count with HAS_PARAMETER count
- Validate parameter types via TYPED_AS chains

### 2. Reference Integrity
- All REFERENCES must point to existing nodes
- Check scope accessibility via CONTAINS hierarchy
- Validate visibility (public/private)

### 3. Data Flow Consistency
- Trace TYPED_AS → Type for parameters
- Follow RETURNS → Type for return values
- Match types along CALLS edges

### 4. Graph Structural Integrity
- No orphaned nodes (all connected to Module root)
- HAS_PARAMETER positions are sequential
- INHERITS doesn't create cycles
