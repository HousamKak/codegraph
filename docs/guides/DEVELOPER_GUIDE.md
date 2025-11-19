# CodeGraph Developer Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture Overview](#architecture-overview)
- [Development Setup](#development-setup)
- [Code Organization](#code-organization)
- [Core Components](#core-components)
- [Extending CodeGraph](#extending-codegraph)
- [Testing](#testing)
- [Debugging](#debugging)
- [Best Practices](#best-practices)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.8+
- Neo4j 5.0+
- Node.js 16+ (for frontend development)
- Git
- Docker (optional, for Neo4j)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/yourusername/codegraph.git
cd codegraph

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install -e .

# Frontend setup
cd ../frontend
npm install

# Start Neo4j
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

---

## Architecture Overview

```
codegraph/
├── backend/
│   ├── codegraph/           # Core library
│   │   ├── db.py            # Neo4j connection & schema
│   │   ├── parser.py        # Python AST parser
│   │   ├── builder.py       # Graph construction
│   │   ├── query.py         # Query interface
│   │   ├── validators.py    # Conservation law validators
│   │   ├── snapshot.py      # Snapshot management
│   │   ├── git_snapshot.py  # Git integration
│   │   ├── mcp_server.py    # MCP server (13 tools)
│   │   └── workflow.py      # Workflow automation
│   ├── app/                 # FastAPI REST API
│   │   ├── main.py          # API endpoints
│   │   ├── models.py        # Pydantic models
│   │   ├── database.py      # DB connection manager
│   │   ├── config.py        # Configuration
│   │   └── routers/         # Route modules
│   ├── examples/            # Example Python files
│   └── tests/               # Test suite
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── api/             # API client
│   │   ├── store/           # Zustand state management
│   │   └── types/           # TypeScript types
│   └── public/
└── docs/                    # Documentation
    ├── theory/              # Academic papers & theory
    ├── architecture/        # System architecture docs
    ├── guides/              # User & developer guides
    ├── tutorials/           # Step-by-step tutorials
    └── examples/            # Code examples
```

---

## Development Setup

### Environment Configuration

Create `backend/.env`:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Logging
LOG_LEVEL=DEBUG

# Development
DEBUG=True
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Running in Development Mode

**Terminal 1: Backend**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2: Frontend**
```bash
cd frontend
npm run dev
```

**Terminal 3: Neo4j Browser** (optional)
```bash
# Access at http://localhost:7474
# Login with neo4j/password
```

---

## Code Organization

### Backend Structure

#### `codegraph/db.py` - Database Layer

**Purpose:** Neo4j connection and schema management

**Key Classes:**
- `CodeGraphDB`: Main database interface
  - `initialize_schema()`: Create indexes and constraints
  - `execute_query()`: Execute Cypher queries
  - `delete_nodes_from_file()`: Clean up before re-indexing
  - `close()`: Clean shutdown

**Example:**
```python
from codegraph.db import CodeGraphDB

db = CodeGraphDB(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)

# Create schema
db.initialize_schema()

# Run query
results = db.execute_query(
    "MATCH (f:Function) RETURN f.name LIMIT 10"
)
```

#### `codegraph/parser.py` - AST Parser

**Purpose:** Parse Python code into entity/relationship graph

**Key Classes:**
- `PythonParser`: AST traversal and entity extraction
  - `parse_file()`: Parse single file
  - `parse_directory()`: Parse entire directory
  - `_extract_function()`: Extract function entities
  - `_extract_class()`: Extract class entities
  - `_extract_calls()`: Extract call relationships

**Entity Types:**
- `FunctionEntity`
- `ClassEntity`
- `ModuleEntity`
- `VariableEntity`
- `ParameterEntity`
- `CallSiteEntity`
- `TypeEntity`
- `DecoratorEntity`
- `UnresolvedReferenceEntity`

**Example:**
```python
from codegraph.parser import PythonParser

parser = PythonParser()
entities, relationships = parser.parse_file("myfile.py")

for entity_id, entity in entities.items():
    print(f"{entity.node_type}: {entity.name}")
```

#### `codegraph/builder.py` - Graph Builder

**Purpose:** Populate Neo4j from parsed entities

**Key Classes:**
- `GraphBuilder`: Converts entities to Cypher
  - `build_graph()`: Main entry point
  - `_create_node()`: Create entity nodes
  - `_create_relationship()`: Create edges

**Example:**
```python
from codegraph.builder import GraphBuilder

builder = GraphBuilder(db)
builder.build_graph(entities, relationships)
```

#### `codegraph/validators.py` - Conservation Laws

**Purpose:** Validate S/R/T conservation laws

**Key Classes:**
- `ConservationValidator`: Main validator
  - `validate_signature_conservation()`: Check arity & types
  - `validate_reference_integrity()`: Check references resolve
  - `validate_data_flow_consistency()`: Check type consistency
  - `validate_structural_integrity()`: Check graph structure
  - `get_validation_report()`: Full report

**Violation Types:**
```python
class ViolationType(Enum):
    SIGNATURE_MISMATCH = "signature_mismatch"
    REFERENCE_BROKEN = "reference_broken"
    DATA_FLOW_INVALID = "data_flow_invalid"
    STRUCTURAL_INVALID = "structural_invalid"
```

**Example:**
```python
from codegraph.validators import ConservationValidator

validator = ConservationValidator(db)
report = validator.get_validation_report()

if report["total_violations"] > 0:
    for violation in report["violations"]:
        print(f"{violation.message} at {violation.location}")
```

#### `codegraph/snapshot.py` - Snapshot Management

**Purpose:** Capture and compare graph states

**Key Classes:**
- `SnapshotManager`: Snapshot operations
  - `create_snapshot()`: Capture current state
  - `compare_snapshots()`: Diff two snapshots
  - `list_snapshots()`: List all snapshots

**Example:**
```python
from codegraph.snapshot import SnapshotManager

sm = SnapshotManager(db)

# Create snapshot
snap1 = sm.create_snapshot("Before refactoring")

# ... make changes ...

# Create another
snap2 = sm.create_snapshot("After refactoring")

# Compare
diff = sm.compare_snapshots(snap1.snapshot_id, snap2.snapshot_id)
print(f"Added: {len(diff.nodes_added)}")
print(f"Modified: {len(diff.nodes_modified)}")
```

#### `codegraph/mcp_server.py` - MCP Server

**Purpose:** Provide 13 tools via Model Context Protocol

**Key Functions:**
- `handle_list_tools()`: Return available tools
- `handle_call_tool()`: Execute tool by name
- Individual tool handlers (13 total)

See [MCP_SERVER.md](../architecture/MCP_SERVER.md) for complete documentation.

---

## Core Components

### 1. AST Parsing

The parser uses Python's built-in `ast` module to traverse source code.

**Adding a New Entity Type:**

```python
# 1. Define entity class in parser.py
@dataclass
class AttributeEntity(Entity):
    """Represents a class attribute."""
    class_id: str
    type_annotation: Optional[str] = None

# 2. Add parsing logic
class PythonParser:
    def _extract_attributes(self, class_node, class_id):
        attributes = []
        for node in class_node.body:
            if isinstance(node, ast.AnnAssign):
                attr_id = f"{class_id}.{node.target.id}"
                attr = AttributeEntity(
                    id=attr_id,
                    name=node.target.id,
                    location=self._get_location(node),
                    node_type="Attribute",
                    class_id=class_id,
                    type_annotation=ast.unparse(node.annotation)
                )
                attributes.append(attr)
        return attributes
```

### 2. Graph Schema

Node and edge types are defined in `backend/schema.md`.

**Adding a New Node Type:**

```python
# 1. Update builder.py
def _create_node(self, entity: Entity):
    if isinstance(entity, AttributeEntity):
        properties = {
            "id": entity.id,
            "name": entity.name,
            "location": entity.location,
            "class_id": entity.class_id,
        }
        if entity.type_annotation:
            properties["type_annotation"] = entity.type_annotation

        self._create_node_cypher("Attribute", properties)
```

**Adding a New Relationship Type:**

```python
# 1. Define in parser.py
@dataclass
class Relationship:
    source_id: str
    target_id: str
    rel_type: str  # e.g., "HAS_ATTRIBUTE"
    properties: Dict[str, Any] = field(default_factory=dict)

# 2. Update builder.py
def _create_relationship(self, rel: Relationship, entities: Dict):
    if rel.rel_type == "HAS_ATTRIBUTE":
        query = """
        MATCH (c:Class {id: $source_id})
        MATCH (a:Attribute {id: $target_id})
        MERGE (c)-[:HAS_ATTRIBUTE]->(a)
        """
        self.db.execute_query(query, {
            "source_id": rel.source_id,
            "target_id": rel.target_id
        })
```

### 3. Conservation Law Validators

**Adding a Custom Validator:**

```python
# In validators.py
class ConservationValidator:
    def validate_custom_rule(self) -> List[Violation]:
        """Check that all public functions have docstrings."""
        violations = []

        query = """
        MATCH (f:Function {visibility: 'public'})
        WHERE f.docstring IS NULL OR f.docstring = ''
        RETURN f.id, f.qualified_name, f.location
        """

        results = self.db.execute_query(query)

        for record in results:
            violations.append(Violation(
                violation_type=ViolationType.STRUCTURAL_INVALID,
                severity="warning",
                entity_id=record["f.id"],
                message=f"Public function {record['f.qualified_name']} missing docstring",
                details={"location": record["f.location"]},
                suggested_fix="Add docstring to document function purpose",
                **self._extract_location_dict(record["f.location"])
            ))

        return violations
```

**Using the Custom Validator:**

```python
# Add to get_validation_report()
def get_validation_report(self) -> Dict[str, Any]:
    violations = []

    # Existing validators
    violations.extend(self.validate_signature_conservation())
    violations.extend(self.validate_reference_integrity())
    violations.extend(self.validate_data_flow_consistency())
    violations.extend(self.validate_structural_integrity())

    # Add custom validator
    violations.extend(self.validate_custom_rule())

    # ... rest of method
```

### 4. Query Interface

**Adding a New Query Method:**

```python
# In query.py
class QueryInterface:
    def find_unused_functions(self) -> List[Dict]:
        """Find functions that are never called."""
        query = """
        MATCH (f:Function)
        WHERE NOT (f)<-[:RESOLVES_TO]-(:CallSite)
        AND f.visibility = 'public'
        RETURN f.id, f.qualified_name, f.location
        ORDER BY f.qualified_name
        """

        results = self.db.execute_query(query)
        return [dict(record) for record in results]
```

---

## Extending CodeGraph

### Adding Support for a New Language

**Example: Adding JavaScript Support**

1. **Create Parser**

```python
# codegraph/parser_js.py
from typing import List, Dict, Any, Tuple
import esprima  # JavaScript parser

class JavaScriptParser:
    def parse_file(self, file_path: str) -> Tuple[Dict, List]:
        with open(file_path, 'r') as f:
            code = f.read()

        ast = esprima.parseScript(code, {'loc': True})
        entities = {}
        relationships = []

        # Traverse AST and extract entities
        self._extract_functions(ast, entities, relationships)
        self._extract_classes(ast, entities, relationships)

        return entities, relationships

    def _extract_functions(self, ast, entities, relationships):
        # Implementation specific to JavaScript AST
        pass
```

2. **Update Builder**

```python
# In builder.py
def build_graph(self, entities: Dict[str, Entity], relationships: List[Relationship], language: str = "python"):
    # Language-specific handling if needed
    for entity_id, entity in entities.items():
        self._create_node(entity, language=language)
```

3. **Update Validators**

```python
# In validators.py
def validate_signature_conservation(self, language: str = "python") -> List[Violation]:
    if language == "javascript":
        # JavaScript-specific validation
        pass
    else:
        # Python validation
        pass
```

### Adding MCP Tools

**Example: Add `get_class_hierarchy` Tool**

```python
# In mcp_server.py

# 1. Add to tool list
TOOLS = [
    # ... existing tools ...
    Tool(
        name="get_class_hierarchy",
        description="Get complete inheritance hierarchy for a class",
        inputSchema={
            "type": "object",
            "properties": {
                "class_id": {
                    "type": "string",
                    "description": "Class node ID"
                },
                "include_methods": {
                    "type": "boolean",
                    "description": "Include methods from parent classes",
                    "default": False
                }
            },
            "required": ["class_id"]
        }
    )
]

# 2. Add handler
async def handle_call_tool(self, name: str, arguments: dict) -> List[TextContent]:
    if name == "get_class_hierarchy":
        return await self._get_class_hierarchy(arguments)
    # ... other tools ...

# 3. Implement logic
async def _get_class_hierarchy(self, args: dict) -> List[TextContent]:
    class_id = args["class_id"]
    include_methods = args.get("include_methods", False)

    # Query hierarchy
    query = """
    MATCH path = (c:Class {id: $class_id})-[:INHERITS*0..]->(parent:Class)
    RETURN c, parent, path
    ORDER BY length(path) DESC
    """

    results = self.query.db.execute_query(query, {"class_id": class_id})

    hierarchy = {
        "class_id": class_id,
        "parents": [],
        "depth": 0
    }

    for record in results:
        parent = dict(record["parent"])
        hierarchy["parents"].append({
            "id": parent["id"],
            "name": parent["qualified_name"],
            "location": parent["location"]
        })

    hierarchy["depth"] = len(hierarchy["parents"])

    # Optionally include methods
    if include_methods:
        # Query methods
        pass

    return [TextContent(
        type="text",
        text=json.dumps(hierarchy, indent=2)
    )]
```

### Adding API Endpoints

**Example: Add Endpoint for Dead Code Detection**

```python
# backend/app/routers/analysis.py
from fastapi import APIRouter, Depends
from ..database import get_db
from codegraph.query import QueryInterface

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/dead-code")
async def find_dead_code(db = Depends(get_db)):
    """Find potentially unused functions."""
    query_interface = QueryInterface(db)

    unused = query_interface.find_unused_functions()

    return {
        "total_unused": len(unused),
        "functions": unused
    }
```

```python
# backend/app/main.py
from .routers import analysis

app.include_router(analysis.router)
```

---

## Testing

### Unit Tests

```python
# backend/tests/test_parser.py
import pytest
from codegraph.parser import PythonParser

def test_parse_simple_function():
    code = """
def add(a: int, b: int) -> int:
    return a + b
"""

    parser = PythonParser()
    entities, relationships = parser.parse_string(code)

    # Check function was extracted
    functions = [e for e in entities.values() if e.node_type == "Function"]
    assert len(functions) == 1

    func = functions[0]
    assert func.name == "add"
    assert len(func.parameters) == 2
    assert func.return_type == "int"

def test_parse_function_call():
    code = """
def caller():
    result = target(42)

def target(x):
    return x * 2
"""

    parser = PythonParser()
    entities, relationships = parser.parse_string(code)

    # Check call relationship
    call_rels = [r for r in relationships if r.rel_type == "HAS_CALLSITE"]
    assert len(call_rels) == 1
```

### Integration Tests

```python
# backend/tests/test_integration.py
import pytest
from codegraph import CodeGraphDB, PythonParser, GraphBuilder, ConservationValidator

@pytest.fixture
def db():
    db = CodeGraphDB("bolt://localhost:7687", "neo4j", "password")
    db.initialize_schema()
    yield db
    # Cleanup
    db.execute_query("MATCH (n) DETACH DELETE n")
    db.close()

def test_full_workflow(db):
    # Parse code
    parser = PythonParser()
    entities, relationships = parser.parse_file("examples/example_code.py")

    # Build graph
    builder = GraphBuilder(db)
    builder.build_graph(entities, relationships)

    # Validate
    validator = ConservationValidator(db)
    report = validator.get_validation_report()

    # Should have no violations in example code
    assert report["total_violations"] == 0
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=codegraph --cov-report=html

# Run specific test file
pytest tests/test_parser.py

# Run specific test
pytest tests/test_parser.py::test_parse_simple_function
```

---

## Debugging

### Enable Debug Logging

```python
# Set in .env
LOG_LEVEL=DEBUG

# Or in code
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Neo4j Browser

Access at http://localhost:7474

**Useful Queries:**

```cypher
// View all nodes
MATCH (n) RETURN n LIMIT 100

// View functions and their callers
MATCH (f:Function)<-[:RESOLVES_TO]-(c:CallSite)
RETURN f.name, c.location

// Find orphaned nodes
MATCH (n)
WHERE NOT (n)--()
RETURN n

// Check for duplicate IDs
MATCH (n)
WITH n.id AS id, count(*) AS count
WHERE count > 1
RETURN id, count
```

### MCP Server Debugging

```bash
# Run server directly with logging
cd backend/codegraph
LOG_LEVEL=DEBUG python mcp_server.py

# Send test request
echo '{"method": "tools/list"}' | python mcp_server.py
```

### Common Issues

**Issue: Duplicate nodes after re-indexing**

Solution: Ensure `delete_nodes_from_file()` is called before re-indexing

```python
if not clear:
    db.delete_nodes_from_file(file_path)
```

**Issue: Validation shows false positives**

Solution: Check for signature-transforming decorators

```python
# Add to SIGNATURE_TRANSFORMING_DECORATORS in validators.py
SIGNATURE_TRANSFORMING_DECORATORS = {
    'click.command',
    'property',
    # Add your decorator here
}
```

---

## Best Practices

### 1. Code Style

- Follow PEP 8 for Python
- Use type hints everywhere
- Document all public functions with docstrings
- Use meaningful variable names

```python
# Good
def extract_function_entities(
    ast_node: ast.FunctionDef,
    module_id: str
) -> FunctionEntity:
    """
    Extract a FunctionEntity from an AST node.

    Args:
        ast_node: The AST FunctionDef node
        module_id: ID of the containing module

    Returns:
        FunctionEntity with all properties populated
    """
    # Implementation
```

### 2. Error Handling

Always provide context in errors:

```python
try:
    db.execute_query(query, params)
except Exception as e:
    logger.error(f"Failed to execute query: {query}", exc_info=True)
    raise ValueError(f"Query execution failed: {e}") from e
```

### 3. Performance

- Use MERGE instead of CREATE for idempotency
- Batch operations where possible
- Use indexes for frequent queries
- Limit result sets

```python
# Good: Batched creation
for batch in chunks(entities, 100):
    query = "UNWIND $batch AS entity CREATE (n:Function) SET n = entity"
    db.execute_query(query, {"batch": batch})

# Bad: Individual creates
for entity in entities:
    query = "CREATE (n:Function) SET n = $props"
    db.execute_query(query, {"props": entity})
```

### 4. Testing

- Write tests for all new features
- Test edge cases
- Use fixtures for common setup
- Mock external dependencies

### 5. Documentation

- Update docs when changing APIs
- Include examples in docstrings
- Keep schema.md in sync with code
- Document breaking changes

---

## Contributing

### Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Make changes
4. Add tests
5. Run tests: `pytest`
6. Update documentation
7. Commit: `git commit -m "feat: add my feature"`
8. Push: `git push origin feature/my-feature`
9. Create Pull Request

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add class hierarchy tool to MCP server
fix: handle missing type annotations in validator
docs: update developer guide with testing section
refactor: simplify parser entity extraction
test: add integration tests for snapshot comparison
```

### Code Review Checklist

- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Code follows style guide
- [ ] No security vulnerabilities
- [ ] Performance considered
- [ ] Error handling adequate

---

## Resources

- [Neo4j Cypher Documentation](https://neo4j.com/docs/cypher-manual/)
- [Python AST Documentation](https://docs.python.org/3/library/ast.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [Conservation Laws Theory](../theory/THEORY_SUMMARY.md)

---

## Getting Help

- GitHub Issues: [repository/issues]
- Discussions: [repository/discussions]
- Discord: [link]
- Email: [email]

---

**Last Updated:** 2025-01-19
**Version:** 1.0.0
