"""Integration tests for CodeGraph v2 schema."""

import pytest
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from codegraph import CodeGraphDB, PythonParser, GraphBuilder, QueryInterface


@pytest.fixture(scope="module")
def db():
    """Create a test database connection."""
    database = CodeGraphDB(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "password")
    )
    yield database
    database.close()


@pytest.fixture(scope="module")
def sample_graph(db):
    """Parse and build a sample graph for testing."""
    # Clear database
    db.clear_database()
    db.initialize_schema()

    # Create a simple test file
    test_code = '''
"""Test module for schema validation."""

class Calculator:
    """A simple calculator."""

    def add(self, x, y):
        """Add two numbers."""
        return x + y

    def multiply(self, x, y):
        """Multiply two numbers."""
        return x * y

def main():
    """Main function."""
    calc = Calculator()
    result = calc.add(5, 3)
    product = calc.multiply(result, 2)
    return product

if __name__ == "__main__":
    main()
'''

    # Write test file
    test_file = "/tmp/test_schema_v2.py"
    with open(test_file, "w") as f:
        f.write(test_code)

    # Parse and build graph
    parser = PythonParser()
    entities, relationships = parser.parse_file(test_file)

    builder = GraphBuilder(db)
    builder.build_graph(entities, relationships)

    # Clean up
    os.remove(test_file)

    return db


class TestSchemaV2Relationships:
    """Test that v2 schema uses correct relationship types."""

    def test_no_old_relationships(self, sample_graph):
        """Verify old relationship types don't exist."""
        # CALLS should not exist
        result = sample_graph.execute_query(
            "MATCH ()-[r:CALLS]->() RETURN count(r) as count"
        )
        assert result[0]["count"] == 0, "CALLS relationship should not exist in v2"

        # DEFINES should not exist
        result = sample_graph.execute_query(
            "MATCH ()-[r:DEFINES]->() RETURN count(r) as count"
        )
        assert result[0]["count"] == 0, "DEFINES relationship should not exist in v2"

        # CONTAINS should not exist
        result = sample_graph.execute_query(
            "MATCH ()-[r:CONTAINS]->() RETURN count(r) as count"
        )
        assert result[0]["count"] == 0, "CONTAINS relationship should not exist in v2"

    def test_new_relationships_exist(self, sample_graph):
        """Verify new relationship types exist."""
        # RESOLVES_TO should exist (replaces CALLS)
        result = sample_graph.execute_query(
            "MATCH ()-[r:RESOLVES_TO]->() RETURN count(r) as count"
        )
        assert result[0]["count"] > 0, "RESOLVES_TO relationship should exist in v2"

        # DECLARES should exist (replaces DEFINES)
        result = sample_graph.execute_query(
            "MATCH ()-[r:DECLARES]->() RETURN count(r) as count"
        )
        assert result[0]["count"] > 0, "DECLARES relationship should exist in v2"

        # HAS_CALLSITE should exist
        result = sample_graph.execute_query(
            "MATCH ()-[r:HAS_CALLSITE]->() RETURN count(r) as count"
        )
        assert result[0]["count"] > 0, "HAS_CALLSITE relationship should exist in v2"

    def test_relationship_count(self, sample_graph):
        """Verify we have exactly 14 relationship types."""
        result = sample_graph.execute_query("""
            MATCH ()-[r]->()
            RETURN DISTINCT type(r) as rel_type
            ORDER BY rel_type
        """)

        rel_types = [r["rel_type"] for r in result]

        # v2 schema should have at most 14 types
        assert len(rel_types) <= 14, f"Expected max 14 relationship types, got {len(rel_types)}: {rel_types}"

        # Should not include old types
        assert "CALLS" not in rel_types
        assert "DEFINES" not in rel_types
        assert "CONTAINS" not in rel_types


class TestCallSiteNodes:
    """Test CallSite node structure and relationships."""

    def test_callsite_nodes_exist(self, sample_graph):
        """Verify CallSite nodes are created."""
        result = sample_graph.execute_query(
            "MATCH (cs:CallSite) RETURN count(cs) as count"
        )
        assert result[0]["count"] > 0, "CallSite nodes should exist"

    def test_callsite_has_caller(self, sample_graph):
        """Verify all CallSite nodes have incoming HAS_CALLSITE relationship."""
        result = sample_graph.execute_query("""
            MATCH (cs:CallSite)
            WHERE NOT ()-[:HAS_CALLSITE]->(cs)
            RETURN count(cs) as orphaned_count
        """)
        assert result[0]["orphaned_count"] == 0, "All CallSites should have a caller"

    def test_callsite_properties(self, sample_graph):
        """Verify CallSite nodes have required properties."""
        result = sample_graph.execute_query("""
            MATCH (cs:CallSite)
            RETURN cs.id as id, cs.arg_count as arg_count, cs.location as location
            LIMIT 1
        """)

        assert len(result) > 0, "Should have at least one CallSite"
        cs = result[0]
        assert cs["id"] is not None, "CallSite should have id"
        assert cs["arg_count"] is not None, "CallSite should have arg_count"
        assert cs["location"] is not None, "CallSite should have location"

    def test_resolved_callsite_pattern(self, sample_graph):
        """Verify resolved calls follow correct pattern: Function -> CallSite -> Function."""
        result = sample_graph.execute_query("""
            MATCH (caller:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(callee:Function)
            RETURN caller.name as caller_name, callee.name as callee_name, cs.resolution_status as status
        """)

        assert len(result) > 0, "Should have at least one resolved call"

        for call in result:
            assert call["caller_name"] is not None
            assert call["callee_name"] is not None
            # Resolution status should be 'resolved' for successful resolution
            if call["status"]:
                assert call["status"] in ["resolved", "unresolved"]


class TestDeclaresRelationship:
    """Test DECLARES relationship replaces DEFINES."""

    def test_class_declares_methods(self, sample_graph):
        """Verify classes use DECLARES for methods."""
        result = sample_graph.execute_query("""
            MATCH (c:Class)-[:DECLARES]->(m:Function)
            RETURN c.name as class_name, collect(m.name) as methods
        """)

        assert len(result) > 0, "Should find class methods via DECLARES"

        # Should find Calculator class with add and multiply methods
        calc = [r for r in result if r["class_name"] == "Calculator"]
        assert len(calc) > 0, "Should find Calculator class"
        assert "add" in calc[0]["methods"], "Should declare add method"
        assert "multiply" in calc[0]["methods"], "Should declare multiply method"

    def test_module_declares_functions(self, sample_graph):
        """Verify modules use DECLARES for top-level functions."""
        result = sample_graph.execute_query("""
            MATCH (m:Module)-[:DECLARES]->(f:Function)
            WHERE NOT (f)<-[:DECLARES]-(:Class)
            RETURN m.name as module_name, collect(f.name) as functions
        """)

        assert len(result) > 0, "Should find module-level functions via DECLARES"

        # Should find main function
        functions = result[0]["functions"]
        assert "main" in functions, "Should declare main function"

    def test_no_defines_relationship(self, sample_graph):
        """Verify DEFINES relationship is not used."""
        result = sample_graph.execute_query("""
            MATCH (c:Class)-[:DEFINES]->(m:Function)
            RETURN count(m) as count
        """)

        assert result[0]["count"] == 0, "DEFINES should not be used (replaced by DECLARES)"


class TestQueryInterface:
    """Test QueryInterface works with v2 schema."""

    def test_find_callers(self, sample_graph):
        """Test find_callers uses RESOLVES_TO pattern."""
        query = QueryInterface(sample_graph)

        # Find the add method
        functions = query.find_function(name="add")
        assert len(functions) > 0, "Should find add function"

        add_func = functions[0]

        # Find callers of add
        callers = query.find_callers(add_func["id"])
        assert len(callers) > 0, "add should have callers"

        # Verify caller info includes CallSite metadata
        caller_info = callers[0]
        assert "caller" in caller_info
        assert "arg_count" in caller_info
        assert "location" in caller_info

    def test_find_callees(self, sample_graph):
        """Test find_callees uses RESOLVES_TO pattern."""
        query = QueryInterface(sample_graph)

        # Find main function
        functions = query.find_function(name="main")
        assert len(functions) > 0, "Should find main function"

        main_func = functions[0]

        # Find what main calls
        callees = query.find_callees(main_func["id"])
        assert len(callees) > 0, "main should call other functions"

        # Verify callee info includes CallSite metadata
        callee_info = callees[0]
        assert "callee" in callee_info
        assert "arg_count" in callee_info
        assert "location" in callee_info


class TestSchemaIntegrity:
    """Test overall schema integrity."""

    def test_all_nodes_have_labels(self, sample_graph):
        """Verify all nodes have at least one label."""
        result = sample_graph.execute_query("""
            MATCH (n)
            WHERE size(labels(n)) = 0
            RETURN count(n) as unlabeled_count
        """)
        assert result[0]["unlabeled_count"] == 0, "All nodes should have labels"

    def test_all_nodes_have_ids(self, sample_graph):
        """Verify all nodes have id property."""
        result = sample_graph.execute_query("""
            MATCH (n)
            WHERE n.id IS NULL
            RETURN count(n) as no_id_count
        """)
        assert result[0]["no_id_count"] == 0, "All nodes should have id property"

    def test_function_signature_conservation(self, sample_graph):
        """Verify functions have signatures."""
        result = sample_graph.execute_query("""
            MATCH (f:Function)
            WHERE f.signature IS NULL
            RETURN count(f) as no_signature_count
        """)
        assert result[0]["no_signature_count"] == 0, "All functions should have signatures"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
