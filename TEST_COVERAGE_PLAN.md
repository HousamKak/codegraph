# CodeGraph Comprehensive Test Coverage Plan

**Version:** 1.0
**Date:** 2025-11-19
**Status:** Initial Planning Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Backend Test Coverage Plan](#backend-test-coverage-plan)
3. [Frontend Test Coverage Plan](#frontend-test-coverage-plan)
4. [Integration & E2E Testing](#integration--e2e-testing)
5. [Testing Infrastructure Setup](#testing-infrastructure-setup)
6. [Coverage Goals & Metrics](#coverage-goals--metrics)
7. [Implementation Timeline](#implementation-timeline)

---

## Executive Summary

### Overview

CodeGraph is a sophisticated code analysis platform with:
- **Backend**: Python FastAPI + Neo4j (~9,833 lines)
- **Frontend**: React + TypeScript (~5,931 lines)
- **Current Test Coverage**: 0% (no tests exist)
- **Target Coverage**: 80%+ overall, 90%+ for critical paths

### Key Challenges

1. **Neo4j Testing**: Requires test database or sophisticated mocking
2. **WebSocket Testing**: Real-time functionality needs special handling
3. **D3 Visualization Testing**: Complex DOM manipulation and SVG rendering
4. **Async Operations**: Heavy use of async/await patterns in both backend and frontend

### Testing Strategy

- **Unit Tests**: 70% of total test effort (isolated component/function testing)
- **Integration Tests**: 20% of total effort (API endpoints, service interactions)
- **E2E Tests**: 10% of total effort (critical user workflows)

---

## Backend Test Coverage Plan

### 1. Testing Stack

```python
# Core Testing Dependencies
pytest==8.0.0                    # Main test framework
pytest-asyncio==0.23.0           # Async test support
pytest-cov==4.1.0                # Coverage reporting
pytest-mock==3.12.0              # Mocking utilities
httpx==0.26.0                    # FastAPI test client
freezegun==1.4.0                 # Time mocking

# Neo4j Testing
neo4j-test-harness==5.0.0        # Test database (if available)
# OR use testcontainers-neo4j for Docker-based testing
# OR implement custom Neo4j mock using pytest fixtures

# Additional Utilities
faker==22.0.0                    # Test data generation
coverage[toml]==7.4.0            # Coverage with TOML config
```

### 2. Test Directory Structure

```
tests/
├── unit/
│   ├── core/
│   │   ├── test_parser.py              # Parser unit tests
│   │   ├── test_validator.py           # Validator unit tests
│   │   ├── test_builder.py             # Graph builder tests
│   │   ├── test_db.py                  # Database layer tests
│   │   └── test_query.py               # Query interface tests
│   ├── snapshots/
│   │   ├── test_manual_snapshots.py    # Manual snapshot tests
│   │   └── test_git_snapshots.py       # Git snapshot tests
│   ├── utils/
│   │   ├── test_file_watcher.py        # File watcher tests
│   │   └── test_workflow.py            # Workflow orchestrator tests
│   └── mcp/
│       └── test_mcp_server.py          # MCP server tests
├── integration/
│   ├── api/
│   │   ├── test_graph_routes.py        # Graph API tests
│   │   ├── test_function_routes.py     # Function API tests
│   │   ├── test_indexing_routes.py     # Indexing API tests
│   │   ├── test_validation_routes.py   # Validation API tests
│   │   ├── test_snapshot_routes.py     # Snapshot API tests
│   │   ├── test_git_routes.py          # Git API tests
│   │   ├── test_file_routes.py         # File API tests
│   │   ├── test_analysis_routes.py     # Analysis API tests
│   │   ├── test_watch_routes.py        # Watch API tests
│   │   └── test_websocket.py           # WebSocket tests
│   └── workflows/
│       ├── test_index_and_validate.py  # Full workflow tests
│       └── test_snapshot_workflow.py   # Snapshot workflows
├── fixtures/
│   ├── db_fixtures.py                  # Neo4j database fixtures
│   ├── api_fixtures.py                 # FastAPI test client fixtures
│   ├── sample_code_fixtures.py         # Sample Python code for parsing
│   └── mock_data.py                    # Mock data generators
├── conftest.py                         # Shared pytest configuration
└── README.md                           # Testing documentation
```

### 3. Unit Test Coverage Plan

#### 3.1 Parser Tests (`codegraph/core/parser.py` - 1,281 lines)

**File**: `tests/unit/core/test_parser.py`

**Test Coverage**: Target 85%+

```python
class TestPythonCodeParser:
    """Tests for PythonCodeParser class"""

    # Basic Parsing Tests
    def test_parse_simple_function()
    def test_parse_function_with_parameters()
    def test_parse_function_with_type_annotations()
    def test_parse_function_with_decorators()
    def test_parse_async_function()
    def test_parse_generator_function()

    # Class Parsing Tests
    def test_parse_simple_class()
    def test_parse_class_with_inheritance()
    def test_parse_class_with_methods()
    def test_parse_dataclass()
    def test_parse_nested_classes()

    # Import Parsing Tests
    def test_parse_simple_import()
    def test_parse_from_import()
    def test_parse_import_with_alias()
    def test_parse_relative_imports()
    def test_parse_wildcard_import()

    # Variable/Attribute Tests
    def test_parse_module_level_variable()
    def test_parse_class_attribute()
    def test_parse_instance_attribute()
    def test_parse_typed_variable()

    # Relationship Extraction Tests
    def test_extract_function_calls()
    def test_extract_class_instantiation()
    def test_extract_method_calls()
    def test_extract_attribute_access()
    def test_extract_inheritance_relationships()

    # Type Extraction Tests
    def test_extract_parameter_types()
    def test_extract_return_types()
    def test_extract_variable_types()
    def test_extract_generic_types()
    def test_extract_union_types()
    def test_extract_optional_types()

    # Edge Cases
    def test_parse_empty_file()
    def test_parse_syntax_error_file()
    def test_parse_file_with_encoding_issues()
    def test_parse_very_large_file()
    def test_parse_deeply_nested_code()

    # Location Tracking Tests
    def test_line_number_tracking()
    def test_column_offset_tracking()
    def test_end_line_tracking()

class TestEntityExtraction:
    """Tests for entity extraction methods"""

    def test_extract_all_entities()
    def test_filter_entities_by_type()
    def test_entity_uniqueness()
    def test_entity_qualified_names()

class TestRelationshipExtraction:
    """Tests for relationship extraction methods"""

    def test_extract_all_relationships()
    def test_filter_relationships_by_type()
    def test_relationship_source_target_linking()
    def test_handle_unresolved_references()
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Foundation of entire system)

---

#### 3.2 Validator Tests (`codegraph/core/validators.py` - 2,069 lines)

**File**: `tests/unit/core/test_validator.py`

**Test Coverage**: Target 90%+ (Critical path)

```python
class TestConservationLaws:
    """Tests for 4 conservation law validators"""

    # S1: Entity Conservation
    def test_s1_all_entities_have_nodes()
    def test_s1_detect_missing_function_nodes()
    def test_s1_detect_missing_class_nodes()
    def test_s1_detect_extra_nodes_not_in_code()
    def test_s1_handle_deleted_entities()

    # S2: Relationship Conservation
    def test_s2_all_relationships_have_edges()
    def test_s2_detect_missing_call_edges()
    def test_s2_detect_missing_inheritance_edges()
    def test_s2_detect_extra_edges_not_in_code()

    # S3: Property Conservation
    def test_s3_all_properties_match_source()
    def test_s3_detect_incorrect_name()
    def test_s3_detect_incorrect_line_number()
    def test_s3_detect_incorrect_type_annotation()
    def test_s3_detect_missing_properties()

    # S4: Structural Isomorphism
    def test_s4_graph_structure_matches_ast()
    def test_s4_detect_structural_mismatches()
    def test_s4_validate_parent_child_relationships()

class TestReferenceValidation:
    """Tests for reference resolution validation"""

    # R1: All Definitions Resolved
    def test_r1_all_references_resolved()
    def test_r1_detect_unresolved_function_call()
    def test_r1_detect_unresolved_class_reference()
    def test_r1_detect_unresolved_import()
    def test_r1_allow_builtin_references()
    def test_r1_allow_external_package_references()

    # R2: No Dangling Edges
    def test_r2_no_edges_without_nodes()
    def test_r2_detect_edge_with_missing_source()
    def test_r2_detect_edge_with_missing_target()

class TestTypingValidation:
    """Tests for type system validation"""

    # T1: Type Annotations Present
    def test_t1_function_has_return_type()
    def test_t1_parameter_has_type_annotation()
    def test_t1_variable_has_type_annotation()
    def test_t1_allow_missing_types_in_legacy_code()

    # T2: Type Consistency
    def test_t2_types_match_across_graph()
    def test_t2_detect_type_mismatch()
    def test_t2_validate_generic_types()

class TestIncrementalValidation:
    """Tests for incremental validation after changes"""

    def test_validate_only_changed_files()
    def test_validate_dependencies_of_changed_files()
    def test_propagate_validation_through_call_graph()
    def test_revalidate_after_fix()

class TestValidationReporting:
    """Tests for validation report generation"""

    def test_generate_full_validation_report()
    def test_group_violations_by_law()
    def test_group_violations_by_severity()
    def test_generate_violation_summary()
    def test_export_violations_to_json()
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Core value proposition)

---

#### 3.3 Database Tests (`codegraph/core/db.py` - 710 lines)

**File**: `tests/unit/core/test_db.py`

**Test Coverage**: Target 80%+

```python
class TestCodeGraphDB:
    """Tests for Neo4j database abstraction layer"""

    @pytest.fixture
    def db(self):
        """Fixture providing test database instance"""
        # Option 1: Use in-memory Neo4j (if available)
        # Option 2: Use Docker container with testcontainers
        # Option 3: Mock Neo4j driver
        pass

    # Connection & Schema Tests
    def test_connect_to_database(self, db)
    def test_close_connection(self, db)
    def test_initialize_schema(self, db)
    def test_create_constraints(self, db)
    def test_create_indexes(self, db)

    # Node Operations
    def test_create_node(self, db)
    def test_get_node_by_id(self, db)
    def test_update_node_properties(self, db)
    def test_delete_node(self, db)
    def test_find_nodes_by_type(self, db)
    def test_find_nodes_by_file(self, db)

    # Edge Operations
    def test_create_edge(self, db)
    def test_get_edge_by_id(self, db)
    def test_update_edge_properties(self, db)
    def test_delete_edge(self, db)
    def test_find_edges_by_type(self, db)

    # Batch Operations
    def test_batch_create_nodes(self, db)
    def test_batch_create_edges(self, db)
    def test_batch_update_nodes(self, db)
    def test_batch_delete_nodes(self, db)

    # Query Operations
    def test_execute_cypher_query(self, db)
    def test_execute_parametrized_query(self, db)
    def test_handle_query_errors(self, db)

    # Graph Retrieval
    def test_get_full_graph(self, db)
    def test_get_file_subgraph(self, db)
    def test_get_node_neighbors(self, db)
    def test_get_node_dependencies(self, db)

    # Change Tracking
    def test_mark_node_changed(self, db)
    def test_mark_file_changed(self, db)
    def test_clear_changed_flags(self, db)
    def test_get_changed_nodes(self, db)

    # Transaction Handling
    def test_transaction_commit(self, db)
    def test_transaction_rollback(self, db)
    def test_nested_transactions(self, db)

    # Error Handling
    def test_handle_connection_error(self, db)
    def test_handle_constraint_violation(self, db)
    def test_handle_deadlock(self, db)
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Data layer)

---

#### 3.4 Query Interface Tests (`codegraph/core/query.py` - 381 lines)

**File**: `tests/unit/core/test_query.py`

**Test Coverage**: Target 85%+

```python
class TestQueryInterface:
    """Tests for high-level graph query interface"""

    # Function Queries
    def test_find_function_by_name(self)
    def test_find_function_by_qualified_name(self)
    def test_find_all_functions_in_file(self)
    def test_find_all_functions_in_module(self)

    # Class Queries
    def test_find_class_by_name(self)
    def test_find_class_methods(self)
    def test_find_class_attributes(self)
    def test_find_class_hierarchy(self)

    # Dependency Queries
    def test_get_function_dependencies(self)
    def test_get_function_dependents(self)
    def test_get_transitive_dependencies(self)
    def test_detect_circular_dependencies(self)

    # Call Graph Queries
    def test_get_function_callers(self)
    def test_get_function_callees(self)
    def test_get_call_chain(self)
    def test_build_call_graph(self)

    # Impact Analysis
    def test_analyze_change_impact(self)
    def test_find_affected_functions(self)
    def test_find_affected_tests(self)

    # Search Queries
    def test_search_by_name_pattern(self)
    def test_search_by_type(self)
    def test_full_text_search(self)

    # Statistics
    def test_count_nodes_by_type(self)
    def test_count_edges_by_type(self)
    def test_calculate_graph_metrics(self)
```

**Priority**: ⭐⭐⭐⭐ (High - Core functionality)

---

#### 3.5 Graph Builder Tests (`codegraph/core/builder.py` - 309 lines)

**File**: `tests/unit/core/test_builder.py`

**Test Coverage**: Target 85%+

```python
class TestGraphBuilder:
    """Tests for converting AST entities to graph nodes/edges"""

    # Node Creation
    def test_create_function_node(self)
    def test_create_class_node(self)
    def test_create_variable_node(self)
    def test_create_import_node(self)
    def test_node_id_generation(self)
    def test_node_property_mapping(self)

    # Edge Creation
    def test_create_call_edge(self)
    def test_create_inheritance_edge(self)
    def test_create_import_edge(self)
    def test_create_contains_edge(self)
    def test_edge_id_generation(self)

    # Full Graph Building
    def test_build_graph_from_entities(self)
    def test_build_incremental_graph(self)
    def test_merge_graphs(self)

    # Reference Resolution
    def test_resolve_internal_references(self)
    def test_mark_external_references(self)
    def test_handle_ambiguous_references(self)
```

**Priority**: ⭐⭐⭐⭐ (High)

---

#### 3.6 Snapshot Tests

**Files**:
- `tests/unit/snapshots/test_manual_snapshots.py`
- `tests/unit/snapshots/test_git_snapshots.py`

**Test Coverage**: Target 80%+

```python
class TestManualSnapshots:
    """Tests for manual snapshot functionality"""

    def test_create_snapshot(self)
    def test_create_snapshot_with_name(self)
    def test_list_snapshots(self)
    def test_get_snapshot_by_id(self)
    def test_delete_snapshot(self)
    def test_restore_from_snapshot(self)
    def test_compare_snapshots(self)
    def test_snapshot_metadata(self)

class TestGitSnapshots:
    """Tests for git-based snapshot functionality"""

    def test_list_git_commits(self)
    def test_get_commit_by_sha(self)
    def test_index_commit(self)
    def test_compare_commits(self)
    def test_get_file_at_commit(self)
    def test_get_changed_files_between_commits(self)
    def test_get_file_diff(self)
    def test_handle_missing_commit(self)
```

**Priority**: ⭐⭐⭐ (Medium)

---

#### 3.7 Utilities Tests

**File**: `tests/unit/utils/test_file_watcher.py`

```python
class TestFileWatcher:
    """Tests for file system watching"""

    def test_watch_directory(self)
    def test_detect_file_creation(self)
    def test_detect_file_modification(self)
    def test_detect_file_deletion(self)
    def test_ignore_patterns(self)
    def test_stop_watching(self)
    def test_handle_rapid_changes(self)
```

**File**: `tests/unit/utils/test_workflow.py`

```python
class TestWorkflowOrchestrator:
    """Tests for workflow orchestration"""

    def test_index_and_validate_workflow(self)
    def test_incremental_update_workflow(self)
    def test_snapshot_workflow(self)
    def test_workflow_error_handling(self)
    def test_workflow_rollback_on_error(self)
```

**Priority**: ⭐⭐⭐ (Medium)

---

#### 3.8 MCP Server Tests

**File**: `tests/unit/mcp/test_mcp_server.py`

**Test Coverage**: Target 75%+

```python
class TestMCPServer:
    """Tests for Model Context Protocol server"""

    def test_server_initialization(self)
    def test_handle_query_request(self)
    def test_handle_index_request(self)
    def test_handle_validation_request(self)
    def test_error_response_formatting(self)
    def test_concurrent_requests(self)
```

**Priority**: ⭐⭐ (Low)

---

### 4. Integration Test Coverage Plan

#### 4.1 API Route Tests

**Priority**: ⭐⭐⭐⭐⭐ (Critical - User-facing interface)

**File**: `tests/integration/api/test_graph_routes.py`

```python
class TestGraphRoutes:
    """Integration tests for /api/graph routes"""

    @pytest.fixture
    def client(self):
        """FastAPI test client"""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    def test_get_graph_empty_db(self, client)
    def test_get_graph_after_indexing(self, client)
    def test_get_graph_filter_by_file(self, client)
    def test_get_graph_filter_by_type(self, client)

    def test_get_node_by_id(self, client)
    def test_get_node_not_found(self, client)

    def test_get_node_neighbors(self, client)
    def test_get_node_neighbors_empty(self, client)

    def test_execute_query_valid_cypher(self, client)
    def test_execute_query_invalid_cypher(self, client)
    def test_execute_query_syntax_error(self, client)
```

**File**: `tests/integration/api/test_indexing_routes.py`

```python
class TestIndexingRoutes:
    """Integration tests for /api/index routes"""

    def test_index_single_file(self, client, tmp_path)
    def test_index_directory(self, client, tmp_path)
    def test_index_directory_recursive(self, client, tmp_path)
    def test_index_commit(self, client)

    def test_index_invalid_file(self, client)
    def test_index_syntax_error_file(self, client)
    def test_index_empty_directory(self, client)

    def test_mark_files_changed(self, client)
    def test_propagate_changes(self, client)
    def test_clear_changed_flags(self, client)
```

**File**: `tests/integration/api/test_validation_routes.py`

```python
class TestValidationRoutes:
    """Integration tests for /api/validate routes"""

    def test_validate_all(self, client)
    def test_validate_structural_only(self, client)
    def test_validate_reference_only(self, client)
    def test_validate_typing_only(self, client)

    def test_validation_report_format(self, client)
    def test_validation_with_violations(self, client)
    def test_validation_no_violations(self, client)
```

**File**: `tests/integration/api/test_snapshot_routes.py`

```python
class TestSnapshotRoutes:
    """Integration tests for /api/snapshots routes"""

    def test_create_snapshot(self, client)
    def test_list_snapshots(self, client)
    def test_get_snapshot(self, client)
    def test_delete_snapshot(self, client)
    def test_get_snapshot_graph(self, client)
    def test_compare_snapshots(self, client)
```

**File**: `tests/integration/api/test_git_routes.py`

```python
class TestGitRoutes:
    """Integration tests for /api/git routes"""

    def test_list_commits(self, client)
    def test_get_commit(self, client)
    def test_compare_commits(self, client)
    def test_get_changed_files(self, client)
    def test_get_file_diff(self, client)
```

**File**: `tests/integration/api/test_websocket.py`

```python
class TestWebSocket:
    """Integration tests for WebSocket functionality"""

    def test_websocket_connection(self, client)
    def test_websocket_file_change_notification(self, client)
    def test_websocket_validation_result(self, client)
    def test_websocket_error_handling(self, client)
    def test_websocket_reconnection(self, client)
```

**Coverage for remaining routes**: test_function_routes.py, test_file_routes.py, test_analysis_routes.py, test_watch_routes.py

---

#### 4.2 Workflow Integration Tests

**File**: `tests/integration/workflows/test_index_and_validate.py`

```python
class TestFullIndexingWorkflow:
    """End-to-end workflow tests"""

    def test_index_project_and_validate(self, client, sample_project)
    def test_incremental_update_workflow(self, client, sample_project)
    def test_multi_file_dependency_tracking(self, client, sample_project)
    def test_refactoring_workflow(self, client, sample_project)
```

---

### 5. Test Fixtures & Utilities

**File**: `tests/fixtures/db_fixtures.py`

```python
@pytest.fixture(scope="session")
def neo4j_test_db():
    """Provides a Neo4j test database instance"""
    # Use testcontainers or in-memory Neo4j
    pass

@pytest.fixture(scope="function")
def clean_db(neo4j_test_db):
    """Provides a clean database for each test"""
    # Clear all data between tests
    pass
```

**File**: `tests/fixtures/sample_code_fixtures.py`

```python
@pytest.fixture
def sample_python_function():
    """Returns sample Python function code"""
    return '''
def calculate_sum(a: int, b: int) -> int:
    """Calculate the sum of two numbers."""
    return a + b
'''

@pytest.fixture
def sample_python_class():
    """Returns sample Python class code"""
    return '''
class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b
'''

@pytest.fixture
def sample_project(tmp_path):
    """Creates a sample Python project for testing"""
    # Create directory structure with sample files
    pass
```

---

### 6. Backend Testing Configuration

**File**: `pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=codegraph
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    --cov-fail-under=80
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow-running tests
    requires_neo4j: Tests requiring Neo4j database
    requires_git: Tests requiring git repository
```

**File**: `pyproject.toml` (coverage configuration)

```toml
[tool.coverage.run]
source = ["codegraph", "app"]
omit = [
    "*/tests/*",
    "*/examples/*",
    "*/__pycache__/*",
    "*/venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

---

### 7. Continuous Integration

**File**: `.github/workflows/backend-tests.yml`

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      neo4j:
        image: neo4j:5.0
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
          - 7474:7474

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest
        env:
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: testpassword

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: backend
```

---

## Frontend Test Coverage Plan

### 1. Testing Stack

```json
// package.json devDependencies
{
  "vitest": "^1.2.0",
  "jsdom": "^23.0.0",
  "@testing-library/react": "^14.1.0",
  "@testing-library/jest-dom": "^6.1.0",
  "@testing-library/user-event": "^14.5.0",
  "@vitest/ui": "^1.2.0",
  "@vitest/coverage-v8": "^1.2.0",
  "msw": "^2.0.0",
  "@playwright/test": "^1.40.0"
}
```

### 2. Test Directory Structure

```
frontend/
├── src/
│   └── __tests__/                      # Tests colocated with source
│       ├── unit/
│       │   ├── api/
│       │   │   ├── client.test.ts      # API client unit tests
│       │   │   └── websocket.test.ts   # WebSocket unit tests
│       │   ├── components/
│       │   │   ├── GraphView.test.tsx
│       │   │   ├── FileExplorer.test.tsx
│       │   │   ├── DiffView.test.tsx
│       │   │   ├── ValidationView.test.tsx
│       │   │   ├── QueryPanel.test.tsx
│       │   │   ├── SourceControl.test.tsx
│       │   │   ├── Sidebar.test.tsx
│       │   │   ├── RightPanel.test.tsx
│       │   │   └── ...others
│       │   ├── hooks/
│       │   │   └── useWebSocket.test.ts
│       │   ├── store/
│       │   │   └── index.test.ts       # Zustand store tests
│       │   └── workers/
│       │       └── layoutWorker.test.ts
│       ├── integration/
│       │   ├── api-integration.test.ts
│       │   ├── websocket-integration.test.ts
│       │   └── state-management.test.ts
│       └── e2e/
│           ├── graph-visualization.spec.ts
│           ├── file-browsing.spec.ts
│           ├── validation-workflow.spec.ts
│           └── query-execution.spec.ts
├── test/
│   ├── mocks/
│   │   ├── api.ts                      # MSW API mocks
│   │   ├── websocket.ts                # WebSocket mock
│   │   └── data.ts                     # Mock data generators
│   ├── fixtures/
│   │   ├── graph-data.ts               # Sample graph data
│   │   ├── commits.ts                  # Sample commit data
│   │   └── validation-reports.ts      # Sample validation data
│   ├── setup.ts                        # Test setup file
│   └── utils.tsx                       # Test utilities & custom renders
├── vitest.config.ts
├── playwright.config.ts
└── README.test.md
```

### 3. Unit Test Coverage Plan

#### 3.1 API Client Tests (`src/api/client.ts` - 275 lines)

**File**: `src/__tests__/unit/api/client.test.ts`

**Test Coverage**: Target 90%+

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ApiClient, ApiError } from '@/api/client';

describe('ApiClient', () => {
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient('http://localhost:8000');
  });

  // Graph API Tests
  describe('Graph Operations', () => {
    it('should fetch full graph', async () => {});
    it('should fetch graph filtered by file', async () => {});
    it('should execute cypher query', async () => {});
    it('should get node by id', async () => {});
    it('should get node neighbors', async () => {});
    it('should handle empty graph', async () => {});
  });

  // Statistics Tests
  describe('Statistics', () => {
    it('should fetch graph statistics', async () => {});
    it('should handle missing statistics', async () => {});
  });

  // Snapshot API Tests
  describe('Snapshot Operations', () => {
    it('should list all snapshots', async () => {});
    it('should create snapshot', async () => {});
    it('should delete snapshot', async () => {});
    it('should get snapshot graph', async () => {});
    it('should compare two snapshots', async () => {});
  });

  // Validation API Tests
  describe('Validation Operations', () => {
    it('should run full validation', async () => {});
    it('should run structural validation', async () => {});
    it('should run reference validation', async () => {});
    it('should run typing validation', async () => {});
    it('should parse validation report', async () => {});
  });

  // Indexing API Tests
  describe('Indexing Operations', () => {
    it('should index file', async () => {});
    it('should index directory', async () => {});
    it('should index git commit', async () => {});
    it('should mark files changed', async () => {});
    it('should propagate changes', async () => {});
    it('should clear changed flags', async () => {});
  });

  // Git API Tests
  describe('Git Operations', () => {
    it('should list commits', async () => {});
    it('should get commit details', async () => {});
    it('should compare commits', async () => {});
    it('should get file diff', async () => {});
    it('should list changed files', async () => {});
  });

  // File API Tests
  describe('File Operations', () => {
    it('should list files', async () => {});
    it('should get file graph', async () => {});
    it('should get file history', async () => {});
    it('should get file at commit', async () => {});
  });

  // Error Handling Tests
  describe('Error Handling', () => {
    it('should handle 404 errors', async () => {});
    it('should handle 500 errors', async () => {});
    it('should handle network errors', async () => {});
    it('should handle timeout errors', async () => {});
    it('should throw ApiError with details', async () => {});
  });

  // Request/Response Tests
  describe('Request/Response Handling', () => {
    it('should set correct headers', async () => {});
    it('should parse JSON responses', async () => {});
    it('should handle non-JSON responses', async () => {});
    it('should include query parameters', async () => {});
  });
});
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Backend communication)

---

#### 3.2 WebSocket Client Tests (`src/api/websocket.ts` - 244 lines)

**File**: `src/__tests__/unit/api/websocket.test.ts`

**Test Coverage**: Target 85%+

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { GraphWebSocket, getWebSocket } from '@/api/websocket';

describe('GraphWebSocket', () => {
  let ws: GraphWebSocket;

  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })) as any;
  });

  // Connection Tests
  describe('Connection Management', () => {
    it('should connect to WebSocket server', () => {});
    it('should disconnect from server', () => {});
    it('should handle connection errors', () => {});
    it('should auto-reconnect on disconnect', () => {});
    it('should stop reconnection after max retries', () => {});
    it('should use exponential backoff for reconnection', () => {});
  });

  // Message Handling Tests
  describe('Message Handling', () => {
    it('should handle "connected" message', () => {});
    it('should handle "file_changed" message', () => {});
    it('should handle "file_error" message', () => {});
    it('should handle "graph_update" message', () => {});
    it('should handle "validation_result" message', () => {});
    it('should handle unknown message types', () => {});
    it('should parse JSON messages correctly', () => {});
  });

  // Event Listener Tests
  describe('Event Listeners', () => {
    it('should register event listener', () => {});
    it('should unregister event listener', () => {});
    it('should call listener on matching event', () => {});
    it('should call wildcard listener on all events', () => {});
    it('should call multiple listeners', () => {});
    it('should handle listener errors gracefully', () => {});
  });

  // Singleton Pattern Tests
  describe('Singleton Pattern', () => {
    it('should return same instance with getWebSocket', () => {});
    it('should create new instance after disconnect', () => {});
  });
});
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Real-time updates)

---

#### 3.3 Store Tests (`src/store/index.ts`)

**File**: `src/__tests__/unit/store/index.test.ts`

**Test Coverage**: Target 90%+

```typescript
import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '@/store';
import { renderHook, act } from '@testing-library/react';

describe('Zustand Store', () => {
  beforeEach(() => {
    // Reset store between tests
    const { getState, setState } = useStore;
    setState(getState()); // Reset to initial state
  });

  // Sidebar State Tests
  describe('Sidebar State', () => {
    it('should set sidebar tab', () => {});
    it('should toggle sidebar', () => {});
    it('should resize sidebar', () => {});
  });

  // File Explorer Tests
  describe('File Explorer State', () => {
    it('should set root directory', () => {});
    it('should select file', () => {});
    it('should expand directory', () => {});
    it('should collapse directory', () => {});
    it('should toggle directory expansion', () => {});
  });

  // View Mode Tests
  describe('View Mode State', () => {
    it('should switch to graph view', () => {});
    it('should switch to diff view', () => {});
    it('should switch to validation view', () => {});
  });

  // Graph Data Tests
  describe('Graph Data State', () => {
    it('should set graph data', () => {});
    it('should select node', () => {});
    it('should select edge', () => {});
    it('should clear selection', () => {});
    it('should update node position', () => {});
  });

  // Snapshot Tests
  describe('Snapshot State', () => {
    it('should set snapshots list', () => {});
    it('should select snapshot', () => {});
    it('should add snapshot', () => {});
    it('should remove snapshot', () => {});
  });

  // Git Commit Tests
  describe('Git Commit State', () => {
    it('should set commits list', () => {});
    it('should select commit', () => {});
    it('should set indexing commit', () => {});
  });

  // Diff State Tests
  describe('Diff State', () => {
    it('should set diff data', () => {});
    it('should set compare-from commit', () => {});
    it('should set compare-to commit', () => {});
    it('should set diff highlight mode', () => {});
  });

  // Validation Tests
  describe('Validation State', () => {
    it('should set validation report', () => {});
    it('should clear validation report', () => {});
  });

  // Query Tests
  describe('Query State', () => {
    it('should add query to history', () => {});
    it('should clear query history', () => {});
  });

  // Panel State Tests
  describe('Panel State', () => {
    it('should show/hide left panel', () => {});
    it('should show/hide right panel', () => {});
    it('should show/hide bottom panel', () => {});
    it('should resize panels', () => {});
  });

  // Loading/Error Tests
  describe('Loading and Error State', () => {
    it('should set loading state', () => {});
    it('should set loading message', () => {});
    it('should set error', () => {});
    it('should clear error', () => {});
  });

  // WebSocket Tests
  describe('WebSocket State', () => {
    it('should set websocket connected', () => {});
    it('should set realtime enabled', () => {});
    it('should set last file change', () => {});
  });
});
```

**Priority**: ⭐⭐⭐⭐⭐ (Critical - Application state)

---

#### 3.4 Component Tests

**File**: `src/__tests__/unit/components/GraphView.test.tsx`

**Test Coverage**: Target 70%+

```typescript
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GraphView from '@/components/GraphView';

describe('GraphView Component', () => {
  const mockGraphData = {
    nodes: [
      { id: '1', label: 'function1', type: 'function', x: 100, y: 100 },
      { id: '2', label: 'function2', type: 'function', x: 200, y: 200 },
    ],
    edges: [
      { id: 'e1', source: '1', target: '2', type: 'calls' },
    ],
  };

  // Rendering Tests
  describe('Rendering', () => {
    it('should render SVG canvas', () => {});
    it('should render nodes', () => {});
    it('should render edges', () => {});
    it('should render node labels', () => {});
    it('should render empty state when no data', () => {});
  });

  // Interaction Tests
  describe('Interactions', () => {
    it('should select node on click', () => {});
    it('should select edge on click', () => {});
    it('should clear selection on background click', () => {});
    it('should support zoom in/out', () => {});
    it('should support pan', () => {});
    it('should support drag nodes', () => {});
  });

  // Filtering Tests
  describe('Filtering', () => {
    it('should filter unresolved references', () => {});
    it('should show/hide filtered nodes', () => {});
  });

  // D3 Integration Tests
  describe('D3 Integration', () => {
    it('should initialize D3 simulation', () => {});
    it('should update layout on data change', () => {});
    it('should cleanup D3 on unmount', () => {});
  });
});
```

**File**: `src/__tests__/unit/components/FileExplorer.test.tsx`

```typescript
describe('FileExplorer Component', () => {
  // Tree Navigation Tests
  it('should render file tree', () => {});
  it('should expand directory on click', () => {});
  it('should collapse directory on click', () => {});
  it('should select file on click', () => {});
  it('should support keyboard navigation', () => {});

  // Virtualization Tests
  it('should virtualize long file lists', () => {});
  it('should scroll to selected file', () => {});

  // Filtering Tests
  it('should filter files by name', () => {});
  it('should show only Python files', () => {});
});
```

**File**: `src/__tests__/unit/components/DiffView.test.tsx`

```typescript
describe('DiffView Component', () => {
  it('should render side-by-side diff', () => {});
  it('should render unified diff', () => {});
  it('should highlight added nodes', () => {});
  it('should highlight removed nodes', () => {});
  it('should highlight modified nodes', () => {});
  it('should show diff summary', () => {});
});
```

**File**: `src/__tests__/unit/components/ValidationView.test.tsx`

```typescript
describe('ValidationView Component', () => {
  it('should render validation report', () => {});
  it('should group violations by law', () => {});
  it('should show violation count', () => {});
  it('should filter violations by category', () => {});
  it('should display violation details', () => {});
  it('should virtualize long violation lists', () => {});
});
```

**File**: `src/__tests__/unit/components/QueryPanel.test.tsx`

```typescript
describe('QueryPanel Component', () => {
  it('should render query editor', () => {});
  it('should execute query on submit', () => {});
  it('should show query results', () => {});
  it('should save query to history', () => {});
  it('should load example queries', () => {});
  it('should handle query errors', () => {});
});
```

**File**: `src/__tests__/unit/components/SourceControl.test.tsx`

```typescript
describe('SourceControl Component', () => {
  it('should render commit list', () => {});
  it('should select commit', () => {});
  it('should compare two commits', () => {});
  it('should index commit with progress', () => {});
  it('should show commit details', () => {});
});
```

**Priority for Components**: ⭐⭐⭐⭐ (High - User interface)

---

#### 3.5 Custom Hook Tests

**File**: `src/__tests__/unit/hooks/useWebSocket.test.ts`

**Test Coverage**: Target 85%+

```typescript
import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useWebSocket } from '@/hooks/useWebSocket';

describe('useWebSocket Hook', () => {
  it('should initialize WebSocket connection', () => {});
  it('should handle file_changed events', async () => {});
  it('should handle file_error events', async () => {});
  it('should update store on validation results', async () => {});
  it('should cleanup on unmount', () => {});
  it('should handle reconnection', async () => {});
});
```

**Priority**: ⭐⭐⭐⭐ (High)

---

#### 3.6 Web Worker Tests

**File**: `src/__tests__/unit/workers/layoutWorker.test.ts`

**Test Coverage**: Target 75%+

```typescript
describe('Layout Worker', () => {
  it('should compute node positions using D3 force', async () => {});
  it('should handle empty graph', async () => {});
  it('should handle single node', async () => {});
  it('should terminate cleanly', () => {});
});
```

**Priority**: ⭐⭐⭐ (Medium)

---

### 4. Integration Test Coverage Plan

#### 4.1 API Integration Tests

**File**: `src/__tests__/integration/api-integration.test.ts`

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { ApiClient } from '@/api/client';

const server = setupServer(
  http.get('/api/graph', () => {
    return HttpResponse.json({ nodes: [], edges: [] });
  }),
  // ... more handlers
);

describe('API Integration', () => {
  beforeAll(() => server.listen());
  afterAll(() => server.close());

  it('should fetch graph and update store', async () => {});
  it('should execute query and display results', async () => {});
  it('should index file and refresh graph', async () => {});
  it('should run validation and display violations', async () => {});
  it('should create snapshot and update list', async () => {});
});
```

**Priority**: ⭐⭐⭐⭐ (High)

---

#### 4.2 WebSocket Integration Tests

**File**: `src/__tests__/integration/websocket-integration.test.ts`

```typescript
describe('WebSocket Integration', () => {
  it('should connect and receive messages', async () => {});
  it('should update graph on file_changed event', async () => {});
  it('should show error banner on file_error', async () => {});
  it('should update validation view on validation_result', async () => {});
});
```

**Priority**: ⭐⭐⭐⭐ (High)

---

#### 4.3 State Management Integration Tests

**File**: `src/__tests__/integration/state-management.test.ts`

```typescript
describe('State Management Integration', () => {
  it('should sync multiple components using same state', () => {});
  it('should propagate changes across views', () => {});
  it('should persist state correctly', () => {});
});
```

**Priority**: ⭐⭐⭐ (Medium)

---

### 5. End-to-End Test Coverage Plan

**Tool**: Playwright

**Configuration**: `playwright.config.ts`

```typescript
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './src/__tests__/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

#### 5.1 E2E Test Scenarios

**File**: `src/__tests__/e2e/graph-visualization.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Graph Visualization Workflow', () => {
  test('should load and display graph', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('svg')).toBeVisible();
  });

  test('should select node and show details', async ({ page }) => {
    await page.goto('/');
    await page.click('circle:first-child'); // Click first node
    await expect(page.locator('[data-testid="right-panel"]')).toContainText('Properties');
  });

  test('should zoom and pan graph', async ({ page }) => {
    await page.goto('/');
    await page.mouse.wheel(0, 100); // Zoom
    await page.mouse.move(100, 100);
    await page.mouse.down();
    await page.mouse.move(200, 200); // Pan
    await page.mouse.up();
  });
});
```

**File**: `src/__tests__/e2e/file-browsing.spec.ts`

```typescript
test.describe('File Browsing Workflow', () => {
  test('should browse file tree and load graph', async ({ page }) => {});
  test('should expand/collapse directories', async ({ page }) => {});
  test('should select file and show file graph', async ({ page }) => {});
});
```

**File**: `src/__tests__/e2e/validation-workflow.spec.ts`

```typescript
test.describe('Validation Workflow', () => {
  test('should run validation and display results', async ({ page }) => {});
  test('should filter violations by category', async ({ page }) => {});
  test('should navigate to violation source', async ({ page }) => {});
});
```

**File**: `src/__tests__/e2e/query-execution.spec.ts`

```typescript
test.describe('Query Execution Workflow', () => {
  test('should execute query and display results', async ({ page }) => {});
  test('should save query to history', async ({ page }) => {});
  test('should load example query', async ({ page }) => {});
});
```

**Priority for E2E**: ⭐⭐⭐ (Medium - Catch integration issues)

---

### 6. Frontend Testing Configuration

**File**: `vitest.config.ts`

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData/**',
        'dist/',
      ],
      include: ['src/**/*.{ts,tsx}'],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 75,
        statements: 80,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

**File**: `test/setup.ts`

```typescript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() { return []; }
  unobserve() {}
} as any;
```

**File**: `test/utils.tsx`

```typescript
import { ReactElement } from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>,
) {
  const testQueryClient = createTestQueryClient();

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={testQueryClient}>
        {children}
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

export * from '@testing-library/react';
```

---

### 7. Mock Service Worker Setup

**File**: `test/mocks/api.ts`

```typescript
import { http, HttpResponse } from 'msw';

export const handlers = [
  // Graph API
  http.get('/api/graph', () => {
    return HttpResponse.json({
      nodes: [
        { id: '1', label: 'test_function', type: 'function' },
      ],
      edges: [],
    });
  }),

  // Validation API
  http.get('/api/validate', () => {
    return HttpResponse.json({
      structural: { violations: [] },
      reference: { violations: [] },
      typing: { violations: [] },
    });
  }),

  // ... more handlers
];

export const server = setupServer(...handlers);
```

---

### 8. Continuous Integration

**File**: `.github/workflows/frontend-tests.yml`

```yaml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Run unit tests
        working-directory: ./frontend
        run: npm run test:unit

      - name: Run integration tests
        working-directory: ./frontend
        run: npm run test:integration

      - name: Install Playwright browsers
        working-directory: ./frontend
        run: npx playwright install --with-deps

      - name: Run E2E tests
        working-directory: ./frontend
        run: npm run test:e2e

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/lcov.info
          flags: frontend

      - name: Upload Playwright report
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

---

## Integration & E2E Testing

### 1. Full Stack Integration Tests

**Purpose**: Test frontend + backend working together

**File**: `e2e/full-stack.spec.ts`

```typescript
test.describe('Full Stack Integration', () => {
  test('should index project, validate, and display results', async ({ page }) => {
    // 1. Start backend server
    // 2. Index sample project via API
    // 3. Navigate to frontend
    // 4. Verify graph is displayed
    // 5. Run validation
    // 6. Verify violations are shown
  });

  test('should receive real-time WebSocket updates', async ({ page }) => {
    // 1. Connect frontend
    // 2. Modify file via backend
    // 3. Verify frontend updates automatically
  });
});
```

**Priority**: ⭐⭐⭐ (Medium - Catch integration bugs)

---

## Coverage Goals & Metrics

### Target Coverage Percentages

| Component | Line Coverage | Branch Coverage | Function Coverage |
|-----------|--------------|-----------------|-------------------|
| **Backend** |
| Parser | 85% | 80% | 90% |
| Validators | 90% | 85% | 95% |
| Database | 80% | 75% | 85% |
| API Routes | 85% | 80% | 90% |
| Query Interface | 85% | 80% | 90% |
| Snapshots | 80% | 75% | 85% |
| Utilities | 75% | 70% | 80% |
| **Overall Backend** | **80%** | **75%** | **85%** |
| **Frontend** |
| API Client | 90% | 85% | 95% |
| WebSocket | 85% | 80% | 90% |
| Store | 90% | 85% | 95% |
| Components | 70% | 65% | 75% |
| Hooks | 85% | 80% | 90% |
| **Overall Frontend** | **80%** | **75%** | **85%** |

### Quality Metrics

- **Test Execution Time**: < 5 minutes for full test suite
- **Test Reliability**: < 1% flaky test rate
- **Code Coverage Trend**: Increasing by 5% per quarter
- **Bug Detection Rate**: 80% of bugs caught by tests before production

---

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)

- ✅ Set up testing infrastructure
- ✅ Configure pytest, vitest, playwright
- ✅ Create test directory structure
- ✅ Set up CI/CD pipelines
- ✅ Create mock/fixture utilities

### Phase 2: Backend Unit Tests (Weeks 3-5)

- ✅ Parser tests (Week 3)
- ✅ Validator tests (Week 3-4)
- ✅ Database tests (Week 4)
- ✅ Query interface tests (Week 5)
- ✅ Graph builder tests (Week 5)

### Phase 3: Backend Integration Tests (Week 6)

- ✅ API route tests
- ✅ WebSocket tests
- ✅ Workflow tests

### Phase 4: Frontend Unit Tests (Weeks 7-9)

- ✅ API client tests (Week 7)
- ✅ WebSocket client tests (Week 7)
- ✅ Store tests (Week 8)
- ✅ Component tests (Week 8-9)
- ✅ Hook tests (Week 9)

### Phase 5: Frontend Integration & E2E Tests (Weeks 10-11)

- ✅ API integration tests (Week 10)
- ✅ State management tests (Week 10)
- ✅ E2E workflow tests (Week 11)

### Phase 6: Full Stack Integration (Week 12)

- ✅ Full stack integration tests
- ✅ Performance tests
- ✅ Load tests

### Phase 7: Refinement & Documentation (Week 13-14)

- ✅ Increase coverage to target percentages
- ✅ Fix flaky tests
- ✅ Write testing documentation
- ✅ Create testing best practices guide

---

## Testing Best Practices

### General Principles

1. **Test Pyramid**: 70% unit, 20% integration, 10% E2E
2. **Fast Feedback**: Unit tests run in < 1 second each
3. **Isolation**: Each test is independent and can run in any order
4. **Clear Names**: Test names describe what is being tested and expected outcome
5. **AAA Pattern**: Arrange, Act, Assert in every test
6. **DRY**: Use fixtures and utilities to avoid repetition
7. **Coverage ≠ Quality**: Aim for meaningful tests, not just high coverage

### Backend Testing Best Practices

1. Use fixtures for Neo4j database setup
2. Mock external dependencies (filesystem, network)
3. Test both success and failure paths
4. Test edge cases (empty input, very large input, etc.)
5. Use parametrized tests for similar test cases
6. Async tests should use `pytest-asyncio`
7. Clear database between tests

### Frontend Testing Best Practices

1. Use `@testing-library/react` for component tests
2. Test user behavior, not implementation details
3. Mock API calls with MSW
4. Use `renderWithProviders` for components needing context
5. Prefer `screen.getByRole` over `getByTestId`
6. Test accessibility (ARIA labels, keyboard navigation)
7. Use Playwright for critical user workflows only

---

## Success Criteria

### Test Coverage

- ✅ 80%+ line coverage across both frontend and backend
- ✅ All critical paths have 90%+ coverage
- ✅ No untested public APIs

### Test Quality

- ✅ All tests pass reliably
- ✅ < 1% flaky test rate
- ✅ Tests run in CI/CD pipeline
- ✅ Coverage reports generated automatically

### Developer Experience

- ✅ Tests run quickly (< 5 minutes for full suite)
- ✅ Clear error messages when tests fail
- ✅ Easy to add new tests
- ✅ Well-documented testing practices

---

## Next Steps

1. **Review & Approve** this test coverage plan
2. **Set up testing infrastructure** (Phase 1)
3. **Begin implementation** following the timeline
4. **Track progress** using coverage reports
5. **Iterate** based on findings and feedback

---

**Document Version**: 1.0
**Last Updated**: 2025-11-19
**Owner**: Engineering Team
**Status**: Ready for Implementation
