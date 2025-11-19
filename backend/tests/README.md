# CodeGraph Test Suite

## Running Tests

### Prerequisites

1. **Neo4j running:**
   ```bash
   docker ps | grep neo4j
   # Should show codegraph-neo4j container running
   ```

2. **Install test dependencies:**
   ```bash
   cd backend
   pip install pytest
   ```

### Run All Tests

```bash
cd backend
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_schema_v2.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_schema_v2.py::TestSchemaV2Relationships -v
```

### Run Specific Test Method

```bash
pytest tests/test_schema_v2.py::TestSchemaV2Relationships::test_no_old_relationships -v
```

## Test Coverage

### Schema v2 Tests (`test_schema_v2.py`)

Tests for the new optimized schema:

- **TestSchemaV2Relationships**: Verifies old relationships removed, new ones exist
- **TestCallSiteNodes**: Tests CallSite node structure and integrity
- **TestDeclaresRelationship**: Tests DECLARES replaces DEFINES
- **TestQueryInterface**: Tests high-level API works with v2 schema
- **TestSchemaIntegrity**: Overall graph integrity checks

### Example Test Output

```
tests/test_schema_v2.py::TestSchemaV2Relationships::test_no_old_relationships PASSED
tests/test_schema_v2.py::TestSchemaV2Relationships::test_new_relationships_exist PASSED
tests/test_schema_v2.py::TestSchemaV2Relationships::test_relationship_count PASSED
tests/test_schema_v2.py::TestCallSiteNodes::test_callsite_nodes_exist PASSED
tests/test_schema_v2.py::TestCallSiteNodes::test_callsite_has_caller PASSED
tests/test_schema_v2.py::TestCallSiteNodes::test_callsite_properties PASSED
tests/test_schema_v2.py::TestCallSiteNodes::test_resolved_callsite_pattern PASSED
tests/test_schema_v2.py::TestDeclaresRelationship::test_class_declares_methods PASSED
tests/test_schema_v2.py::TestDeclaresRelationship::test_module_declares_functions PASSED
tests/test_schema_v2.py::TestDeclaresRelationship::test_no_defines_relationship PASSED
tests/test_schema_v2.py::TestQueryInterface::test_find_callers PASSED
tests/test_schema_v2.py::TestQueryInterface::test_find_callees PASSED
tests/test_schema_v2.py::TestSchemaIntegrity::test_all_nodes_have_labels PASSED
tests/test_schema_v2.py::TestSchemaIntegrity::test_all_nodes_have_ids PASSED
tests/test_schema_v2.py::TestSchemaIntegrity::test_function_signature_conservation PASSED

============================== 15 passed in 2.34s ===============================
```

## Environment Variables

Configure Neo4j connection via environment variables:

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="password"

pytest tests/
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      neo4j:
        image: neo4j:latest
        env:
          NEO4J_AUTH: neo4j/password
        ports:
          - 7687:7687
          - 7474:7474

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          cd backend
          pip install -e .
          pip install pytest

      - name: Run tests
        run: |
          cd backend
          pytest tests/ -v
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: password
```

## Adding New Tests

1. Create test file in `tests/` directory
2. Import pytest: `import pytest`
3. Create test classes and methods (prefix with `test_`)
4. Use fixtures for database setup
5. Run with `pytest tests/test_yourfile.py -v`

### Example Test Template

```python
import pytest
from codegraph import CodeGraphDB

@pytest.fixture
def db():
    """Database fixture."""
    database = CodeGraphDB()
    yield database
    database.close()

class TestYourFeature:
    """Test your feature."""

    def test_something(self, db):
        """Test something."""
        result = db.execute_query("MATCH (n) RETURN count(n) as count")
        assert result[0]["count"] >= 0
```
