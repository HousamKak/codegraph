"""Unit tests for GraphBuilder."""

import pytest
from codegraph import CodeGraphDB, PythonParser, GraphBuilder


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestGraphBuilder:
    """Tests for GraphBuilder."""

    def test_build_graph_from_entities(self, clean_db, temp_file, parser):
        """Test building graph from parsed entities."""
        code = '''
def hello():
    """Say hello."""
    print("Hello")
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))

        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Verify graph was created
        result = clean_db.execute_query("MATCH (n) RETURN count(n) as count")
        assert result[0]['count'] > 0

    def test_create_function_node(self, clean_db, temp_file, parser):
        """Test creating function nodes."""
        code = '''
def test_func():
    """Test function."""
    pass
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))
        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Check for function node
        result = clean_db.execute_query("""
            MATCH (f:Function)
            WHERE f.name = 'test_func'
            RETURN f
        """)

        assert len(result) >= 1

    def test_create_class_node(self, clean_db, temp_file, parser):
        """Test creating class nodes."""
        code = '''
class MyClass:
    """Test class."""
    pass
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))
        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Check for class node
        result = clean_db.execute_query("""
            MATCH (c:Class)
            WHERE c.name = 'MyClass'
            RETURN c
        """)

        assert len(result) >= 1

    def test_create_module_node(self, clean_db, temp_file, parser):
        """Test creating module nodes."""
        code = '''
"""Test module."""
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))
        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Check for module node
        result = clean_db.execute_query("""
            MATCH (m:Module)
            RETURN m
        """)

        assert len(result) >= 1

    def test_create_relationships(self, clean_db, temp_file, parser):
        """Test creating relationships."""
        code = '''
def caller():
    """Caller function."""
    callee()

def callee():
    """Callee function."""
    pass
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))
        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Check for relationships
        result = clean_db.execute_query("""
            MATCH ()-[r]->()
            RETURN count(r) as count
        """)

        assert result[0]['count'] > 0

    def test_handle_inheritance(self, clean_db, temp_file, parser):
        """Test handling inheritance relationships."""
        code = '''
class Base:
    """Base class."""
    pass

class Derived(Base):
    """Derived class."""
    pass
'''
        temp_file.write_text(code)

        entities, relationships = parser.parse_file(str(temp_file))
        builder = GraphBuilder(clean_db)
        builder.build_graph(entities, relationships)

        # Check for INHERITS relationship
        result = clean_db.execute_query("""
            MATCH ()-[r:INHERITS]->()
            RETURN count(r) as count
        """)

        assert result[0]['count'] >= 1

    def test_build_empty_graph(self, clean_db):
        """Test building graph with no entities."""
        builder = GraphBuilder(clean_db)
        builder.build_graph({}, [])

        # Should not error
        result = clean_db.execute_query("MATCH (n) RETURN count(n) as count")
        assert result[0]['count'] == 0
