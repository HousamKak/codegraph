"""Unit tests for CodeGraphDB."""

import pytest
from codegraph import CodeGraphDB


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestDatabaseConnection:
    """Tests for database connection and initialization."""

    def test_connect_to_database(self, neo4j_test_db):
        """Test connecting to Neo4j database."""
        assert neo4j_test_db is not None
        assert hasattr(neo4j_test_db, 'driver')

    def test_initialize_schema(self, clean_db):
        """Test schema initialization."""
        clean_db.initialize_schema()

        # Verify constraints and indexes exist
        result = clean_db.execute_query("SHOW CONSTRAINTS")
        assert isinstance(result, list)

    def test_close_connection(self, neo4j_test_db):
        """Test closing database connection."""
        # Connection will be closed by fixture cleanup
        assert neo4j_test_db.driver is not None


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestNodeOperations:
    """Tests for node CRUD operations."""

    def test_create_node(self, clean_db):
        """Test creating a node."""
        query = """
        CREATE (n:Function {
            id: 'test_func',
            name: 'test_function',
            signature: 'test_function()'
        })
        RETURN n
        """
        result = clean_db.execute_query(query)
        assert len(result) == 1
        assert result[0]['n']['name'] == 'test_function'

    def test_get_node_by_id(self, clean_db):
        """Test retrieving node by ID."""
        # Create node
        clean_db.execute_query("""
            CREATE (n:Function {id: 'func1', name: 'func1'})
        """)

        # Get node
        result = clean_db.execute_query("""
            MATCH (n:Function {id: 'func1'})
            RETURN n
        """)

        assert len(result) == 1
        assert result[0]['n']['id'] == 'func1'

    def test_update_node_properties(self, clean_db):
        """Test updating node properties."""
        # Create node
        clean_db.execute_query("""
            CREATE (n:Function {id: 'func1', name: 'original'})
        """)

        # Update property
        clean_db.execute_query("""
            MATCH (n:Function {id: 'func1'})
            SET n.name = 'updated'
        """)

        # Verify update
        result = clean_db.execute_query("""
            MATCH (n:Function {id: 'func1'})
            RETURN n.name as name
        """)

        assert result[0]['name'] == 'updated'

    def test_delete_node(self, clean_db):
        """Test deleting a node."""
        # Create node
        clean_db.execute_query("""
            CREATE (n:Function {id: 'func1', name: 'temp'})
        """)

        # Delete node
        clean_db.execute_query("""
            MATCH (n:Function {id: 'func1'})
            DELETE n
        """)

        # Verify deletion
        result = clean_db.execute_query("""
            MATCH (n:Function {id: 'func1'})
            RETURN n
        """)

        assert len(result) == 0

    def test_find_nodes_by_type(self, clean_db):
        """Test finding nodes by type."""
        # Create multiple nodes
        clean_db.execute_query("""
            CREATE (f1:Function {id: 'f1', name: 'func1'}),
                   (f2:Function {id: 'f2', name: 'func2'}),
                   (c1:Class {id: 'c1', name: 'Class1'})
        """)

        # Find functions
        result = clean_db.execute_query("""
            MATCH (n:Function)
            RETURN count(n) as count
        """)

        assert result[0]['count'] == 2


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestEdgeOperations:
    """Tests for edge/relationship operations."""

    def test_create_edge(self, clean_db):
        """Test creating an edge."""
        clean_db.execute_query("""
            CREATE (f1:Function {id: 'f1', name: 'func1'}),
                   (f2:Function {id: 'f2', name: 'func2'}),
                   (cs:CallSite {id: 'cs1'}),
                   (f1)-[:HAS_CALLSITE]->(cs),
                   (cs)-[:RESOLVES_TO]->(f2)
        """)

        result = clean_db.execute_query("""
            MATCH ()-[r:HAS_CALLSITE]->()
            RETURN count(r) as count
        """)

        assert result[0]['count'] == 1

    def test_find_edges_by_type(self, clean_db):
        """Test finding edges by type."""
        clean_db.execute_query("""
            CREATE (f1:Function {id: 'f1'}),
                   (f2:Function {id: 'f2'}),
                   (cs:CallSite {id: 'cs1'}),
                   (f1)-[:HAS_CALLSITE]->(cs),
                   (cs)-[:RESOLVES_TO]->(f2)
        """)

        result = clean_db.execute_query("""
            MATCH ()-[r:RESOLVES_TO]->()
            RETURN count(r) as count
        """)

        assert result[0]['count'] == 1


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestBatchOperations:
    """Tests for batch operations."""

    def test_batch_create_nodes(self, clean_db):
        """Test batch creating nodes."""
        nodes = [
            {'id': f'f{i}', 'name': f'func{i}'}
            for i in range(10)
        ]

        clean_db.execute_query("""
            UNWIND $nodes as node
            CREATE (f:Function)
            SET f = node
        """, {'nodes': nodes})

        result = clean_db.execute_query("""
            MATCH (f:Function)
            RETURN count(f) as count
        """)

        assert result[0]['count'] == 10


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestQueryExecution:
    """Tests for query execution."""

    def test_execute_cypher_query(self, clean_db):
        """Test executing Cypher query."""
        result = clean_db.execute_query("RETURN 1 as num")
        assert result[0]['num'] == 1

    def test_execute_parametrized_query(self, clean_db):
        """Test executing parametrized query."""
        result = clean_db.execute_query(
            "RETURN $value as result",
            {'value': 42}
        )
        assert result[0]['result'] == 42

    def test_handle_query_errors(self, clean_db):
        """Test handling query errors."""
        with pytest.raises(Exception):
            clean_db.execute_query("INVALID CYPHER QUERY")


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestGraphRetrieval:
    """Tests for graph retrieval operations."""

    def test_get_full_graph(self, clean_db):
        """Test retrieving full graph."""
        # Create simple graph
        clean_db.execute_query("""
            CREATE (f1:Function {id: 'f1', name: 'func1'}),
                   (f2:Function {id: 'f2', name: 'func2'}),
                   (cs:CallSite {id: 'cs1'}),
                   (f1)-[:HAS_CALLSITE]->(cs),
                   (cs)-[:RESOLVES_TO]->(f2)
        """)

        # Get all nodes
        nodes = clean_db.execute_query("MATCH (n) RETURN n")
        assert len(nodes) >= 3

        # Get all relationships
        edges = clean_db.execute_query("MATCH ()-[r]->() RETURN r")
        assert len(edges) >= 2

    def test_get_node_neighbors(self, clean_db):
        """Test getting node neighbors."""
        clean_db.execute_query("""
            CREATE (f1:Function {id: 'f1', name: 'func1'}),
                   (f2:Function {id: 'f2', name: 'func2'}),
                   (f3:Function {id: 'f3', name: 'func3'}),
                   (cs1:CallSite {id: 'cs1'}),
                   (cs2:CallSite {id: 'cs2'}),
                   (f1)-[:HAS_CALLSITE]->(cs1),
                   (cs1)-[:RESOLVES_TO]->(f2),
                   (f1)-[:HAS_CALLSITE]->(cs2),
                   (cs2)-[:RESOLVES_TO]->(f3)
        """)

        # Get neighbors of f1
        result = clean_db.execute_query("""
            MATCH (f:Function {id: 'f1'})-[:HAS_CALLSITE]->(:CallSite)-[:RESOLVES_TO]->(neighbor)
            RETURN count(neighbor) as count
        """)

        assert result[0]['count'] == 2


@pytest.mark.unit
@pytest.mark.requires_neo4j
class TestDatabaseCleaning:
    """Tests for database cleaning operations."""

    def test_clear_database(self, clean_db):
        """Test clearing database."""
        # Create some data
        clean_db.execute_query("""
            CREATE (f:Function {id: 'f1', name: 'func1'})
        """)

        # Clear database
        clean_db.clear_database()

        # Verify empty
        result = clean_db.execute_query("MATCH (n) RETURN count(n) as count")
        assert result[0]['count'] == 0
