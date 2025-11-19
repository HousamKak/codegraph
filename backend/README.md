# CodeGraph

A graph database for Python codebases that enforces conservation laws to help LLMs maintain code integrity during modifications.

## Overview

CodeGraph analyzes Python codebases and builds a graph representation in Neo4j, tracking functions, classes, variables, parameters, and their relationships. It enforces **4 conservation laws** that ensure structural integrity when code is modified:

### The 4 Conservation Laws

1. **Signature Conservation**
   - Function signatures (parameters + return type + visibility) must match all call sites
   - Changing a function signature requires updating all callers
   - Ensures arity and type consistency

2. **Reference Integrity**
   - All identifiers must resolve to valid, accessible entities
   - No dangling references or broken imports
   - Scope and visibility rules must be respected

3. **Data Flow Consistency**
   - Types and values flowing through edges must be compatible
   - Type annotations must be consistent across call chains
   - Return types must match usage expectations

4. **Graph Structural Integrity**
   - Edges must connect valid nodes
   - Proper multiplicities maintained (e.g., parameter belongs to exactly one function)
   - No circular dependencies in inheritance
   - Sequential parameter positions

## Installation

### Prerequisites

- Python 3.8+
- Neo4j 5.0+ (running locally or remotely)

### Install Neo4j

**Option 1: Docker (Recommended)**
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

**Option 2: Download from neo4j.com**
- Download from https://neo4j.com/download/
- Install and start the Neo4j service
- Set password to "password" or update the connection settings

### Install CodeGraph

```bash
# Clone the repository
git clone https://github.com/yourusername/codegraph.git
cd codegraph

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### 1. Index a Python codebase

```bash
# Index a single file
codegraph index path/to/file.py --clear

# Index an entire directory
codegraph index path/to/project --clear
```

The `--clear` flag clears the database before indexing.

### 2. Validate conservation laws

```bash
codegraph validate
```

This will check all 4 conservation laws and report violations.

### 3. Query the graph

```bash
# Find a function
codegraph find-function myFunction

# Find all callers of a function
codegraph callers <function_id>

# Analyze dependencies
codegraph dependencies <function_id> --depth 2

# Search for entities
codegraph search "User" --type Class

# Impact analysis
codegraph impact <entity_id> --change-type delete

# View statistics
codegraph stats

# Execute raw Cypher query
codegraph query "MATCH (f:Function) RETURN f.name LIMIT 10"
```

## Usage Examples

### Example 1: Basic Usage

```python
from codegraph import CodeGraphDB, PythonParser, GraphBuilder, QueryInterface, ConservationValidator

# Connect to Neo4j
db = CodeGraphDB(uri="bolt://localhost:7687", user="neo4j", password="password")

# Initialize schema
db.initialize_schema()

# Parse Python code
parser = PythonParser()
entities, relationships = parser.parse_directory("./my_project")

# Build graph
builder = GraphBuilder(db)
builder.build_graph(entities, relationships)

# Query the graph
query = QueryInterface(db)
functions = query.find_function(name="calculate_total")
print(f"Found {len(functions)} functions")

# Validate conservation laws
validator = ConservationValidator(db)
report = validator.get_validation_report()
print(f"Total violations: {report['total_violations']}")

# Close connection
db.close()
```

### Example 2: Impact Analysis Before Modification

```python
from codegraph import CodeGraphDB, QueryInterface

db = CodeGraphDB()
query = QueryInterface(db)

# Find a function
functions = query.find_function(name="process_data")
func_id = functions[0]["id"]

# Analyze impact of deleting this function
impact = query.get_impact_analysis(func_id, "delete")

print(f"Deleting this function would affect:")
print(f"- {len(impact['affected_callers'])} callers")
print(f"- {len(impact['affected_references'])} references")
```

### Example 3: Validate a Proposed Change

```python
from codegraph import CodeGraphDB, ConservationValidator

db = CodeGraphDB()
validator = ConservationValidator(db)

# Validate what would happen if we modify a function
violations = validator.validate_change(
    entity_id="abc123",
    change_type="modify",
    new_properties={"signature": "def calculate(x: int, y: int, z: int) -> float"}
)

if violations:
    print("This change would cause violations:")
    for v in violations:
        print(f"- {v.message}")
        print(f"  Suggested fix: {v.suggested_fix}")
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Interface                        │
│                    (cli.py)                             │
└───────────────────┬─────────────────────────────────────┘
                    │
         ┌──────────┼──────────┐
         │          │          │
         ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌──────────┐
    │ Parser │ │ Query  │ │Validator │
    │        │ │        │ │          │
    └───┬────┘ └───┬────┘ └────┬─────┘
        │          │           │
        │          │           │
        ▼          ▼           ▼
    ┌──────────────────────────────┐
    │      Graph Builder           │
    │      (builder.py)            │
    └──────────────┬───────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │         Neo4j Database        │
    │                              │
    │  Nodes: Function, Class,     │
    │         Variable, Parameter  │
    │                              │
    │  Edges: RESOLVES_TO,         │
    │         DECLARES, etc.       │
    └──────────────────────────────┘
```

## Schema

See [schema.md](schema.md) for detailed graph schema documentation.

### Key Node Types
- **Function**: Represents functions/methods
- **Class**: Represents classes
- **Variable**: Represents variables
- **Parameter**: Function parameters
- **Module**: Python modules/files
- **Type**: Type information

### Key Relationship Types
- **RESOLVES_TO**: CallSite to Function call resolution
- **HAS_CALLSITE**: Function to CallSite relationships
- **HAS_PARAMETER**: Function-to-parameter links
- **DECLARES**: Module/Class declaration relationships
- **REFERENCES**: Reference relationships
- **INHERITS**: Class inheritance
- **TYPED_AS**: Type annotations

## Conservation Law Details

### 1. Signature Conservation
**Purpose**: Ensure function interfaces remain consistent with usage

**Checks**:
- Parameter count matches at all call sites
- Type annotations are compatible
- Visibility rules respected (private functions not called externally)

**Example Violation**:
```python
# Function definition
def calculate(x: int, y: int) -> int:
    return x + y

# Call site - VIOLATION: too many arguments
result = calculate(1, 2, 3)
```

### 2. Reference Integrity
**Purpose**: Ensure all references resolve to valid entities

**Checks**:
- No orphaned nodes (disconnected from the graph)
- All function calls resolve to existing functions
- Imported entities exist
- Variables are defined before use

**Example Violation**:
```python
# VIOLATION: calling non-existent function
result = undefined_function(42)
```

### 3. Data Flow Consistency
**Purpose**: Ensure type safety across the codebase

**Checks**:
- Return type annotations present and consistent
- Parameter type annotations present
- Types match across call chains (when annotated)

**Example Violation**:
```python
def get_name() -> str:
    return 42  # VIOLATION: returns int, not str
```

### 4. Structural Integrity
**Purpose**: Ensure graph structure is valid

**Checks**:
- Parameter positions are sequential (0, 1, 2, ...)
- Each parameter belongs to exactly one function
- No circular inheritance
- No circular dependencies (detected in call graph)

**Example Violation**:
```python
# VIOLATION: circular inheritance
class A(B):
    pass

class B(A):
    pass
```

## Use Cases

### For LLM Code Generation
- **Pre-generation**: Query the graph to understand existing code structure
- **Post-generation**: Validate that generated code respects conservation laws
- **Refactoring**: Ensure changes don't break existing relationships

### For Code Review
- Automatically detect broken references
- Identify signature mismatches
- Find missing type annotations
- Detect circular dependencies

### For Code Understanding
- Visualize call graphs
- Trace data flow
- Understand dependencies
- Find all usages of a function/class

### For Refactoring
- Safe renaming (find all references)
- Impact analysis before deletion
- Signature change validation
- Dependency analysis

## Advanced Features

### Custom Cypher Queries

```bash
# Find all private functions
codegraph query "MATCH (f:Function {visibility: 'private'}) RETURN f.name"

# Find functions with most callers
codegraph query "
  MATCH (cs:CallSite)-[:RESOLVES_TO]->(f:Function)
  RETURN f.name, count(cs) as caller_count
  ORDER BY caller_count DESC
  LIMIT 10
"

# Find classes with no methods
codegraph query "
  MATCH (c:Class)
  WHERE NOT (c)-[:DECLARES]->(:Function)
  RETURN c.name
"
```

### Python API

```python
# Custom validation rules
from codegraph import ConservationValidator

class MyValidator(ConservationValidator):
    def validate_custom_rule(self):
        # Add your own validation logic
        pass

# Custom queries
from codegraph import QueryInterface

query = QueryInterface(db)
results = db.execute_query("""
    MATCH (f:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(callee:Function)
    WHERE callee.name = 'deprecated_function'
    RETURN f.qualified_name
""")
```

## Configuration

### Neo4j Connection

You can configure the Neo4j connection via:

1. **Command line arguments**:
   ```bash
   codegraph --uri bolt://localhost:7687 --user neo4j --password mypassword index .
   ```

2. **Environment variables**:
   ```bash
   export NEO4J_URI=bolt://localhost:7687
   export NEO4J_USER=neo4j
   export NEO4J_PASSWORD=mypassword
   ```

3. **Python code**:
   ```python
   from codegraph import CodeGraphDB
   db = CodeGraphDB(uri="bolt://remote:7687", user="neo4j", password="secret")
   ```

## Troubleshooting

### Neo4j Connection Issues
```bash
# Test connection
docker ps  # Check if Neo4j is running
curl http://localhost:7474  # Check if Neo4j web interface is accessible
```

### Parsing Errors
- Ensure Python files are syntactically valid
- Check file encoding (should be UTF-8)
- Review parser logs for specific errors

### Performance
- For large codebases, indexing may take time
- Consider indexing incrementally
- Use indexes and constraints (automatically created)

## Roadmap

- [ ] Support for more languages (JavaScript, TypeScript, Java)
- [ ] Incremental updates (only re-parse changed files)
- [ ] Web UI for graph visualization
- [ ] Integration with LSP servers
- [ ] Auto-fix suggestions for violations
- [ ] Machine learning for code pattern detection
- [ ] Export to other graph formats (GraphML, DOT)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Credits

Built with:
- [Neo4j](https://neo4j.com/) - Graph database
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- Python AST module - Code parsing
