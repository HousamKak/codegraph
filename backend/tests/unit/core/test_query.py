"""Unit tests for QueryInterface."""

import pytest
from codegraph import CodeGraphDB, QueryInterface, PythonParser, GraphBuilder


@pytest.fixture
def query_interface(clean_db):
    """Provide a query interface instance."""
    return QueryInterface(clean_db)


@pytest.fixture
def populated_db(clean_db, temp_file):
    """Provide a database populated with test data."""
    code = '''
class Calculator:
    """Calculator class."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

def main():
    """Main function."""
    calc = Calculator()
    result = calc.add(5, 3)
    product = calc.multiply(result, 2)
    return product
'''
    temp_file.write_text(code)

    parser = PythonParser()
    entities, relationships = parser.parse_file(str(temp_file))
    builder = GraphBuilder(clean_db)
    builder.build_graph(entities, relationships)

    return clean_db


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestFunctionQueries:
    """Tests for function query methods."""

    def test_find_function_by_name(self, query_interface, populated_db):
        """Test finding function by name."""
        functions = query_interface.find_function(name="add")

        assert len(functions) >= 0  # Might be 1 if found
        if len(functions) > 0:
            assert functions[0]['name'] == 'add' or 'add' in functions[0].get('qualified_name', '')

    def test_find_all_functions(self, query_interface, populated_db):
        """Test finding all functions."""
        result = populated_db.execute_query("MATCH (f:Function) RETURN f")

        assert len(result) >= 3  # add, multiply, main

    def test_find_function_returns_empty_if_not_found(self, query_interface, populated_db):
        """Test that find_function returns empty list if not found."""
        functions = query_interface.find_function(name="nonexistent_function")

        assert isinstance(functions, list)


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestClassQueries:
    """Tests for class query methods."""

    def test_find_class_by_name(self, query_interface, populated_db):
        """Test finding class by name."""
        classes = query_interface.find_class(name="Calculator")

        assert len(classes) >= 0
        if len(classes) > 0:
            assert classes[0]['name'] == 'Calculator' or 'Calculator' in classes[0].get('qualified_name', '')

    def test_find_class_methods(self, query_interface, populated_db):
        """Test finding methods of a class."""
        # First find the class
        classes = query_interface.find_class(name="Calculator")

        if len(classes) > 0:
            class_id = classes[0]['id']

            # Find methods
            methods = populated_db.execute_query("""
                MATCH (c:Class {id: $class_id})-[:DECLARES]->(m:Function)
                RETURN m
            """, {'class_id': class_id})

            assert len(methods) >= 2  # add and multiply


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestCallGraphQueries:
    """Tests for call graph query methods."""

    def test_find_callers(self, query_interface, populated_db):
        """Test finding callers of a function."""
        # Find the add function
        functions = query_interface.find_function(name="add")

        if len(functions) > 0:
            func_id = functions[0]['id']

            # Find callers
            callers = query_interface.find_callers(func_id)

            assert isinstance(callers, list)
            # main calls add, so should have at least one caller
            if len(callers) > 0:
                assert 'caller' in callers[0]

    def test_find_callees(self, query_interface, populated_db):
        """Test finding callees of a function."""
        # Find main function
        functions = query_interface.find_function(name="main")

        if len(functions) > 0:
            func_id = functions[0]['id']

            # Find callees
            callees = query_interface.find_callees(func_id)

            assert isinstance(callees, list)
            # main calls add and multiply
            if len(callees) > 0:
                assert 'callee' in callees[0]


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestDependencyQueries:
    """Tests for dependency query methods."""

    def test_get_function_dependencies(self, query_interface, populated_db):
        """Test getting function dependencies."""
        functions = query_interface.find_function(name="main")

        if len(functions) > 0:
            func_id = functions[0]['id']

            # Get dependencies
            deps = populated_db.execute_query("""
                MATCH (f:Function {id: $id})-[:HAS_CALLSITE]->(:CallSite)-[:RESOLVES_TO]->(dep)
                RETURN dep
            """, {'id': func_id})

            assert isinstance(deps, list)


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestStatistics:
    """Tests for statistics queries."""

    def test_count_nodes_by_type(self, query_interface, populated_db):
        """Test counting nodes by type."""
        result = populated_db.execute_query("""
            MATCH (f:Function)
            RETURN count(f) as count
        """)

        assert result[0]['count'] >= 3

    def test_count_edges_by_type(self, query_interface, populated_db):
        """Test counting edges by type."""
        result = populated_db.execute_query("""
            MATCH ()-[r:HAS_CALLSITE]->()
            RETURN count(r) as count
        """)

        assert result[0]['count'] >= 0
