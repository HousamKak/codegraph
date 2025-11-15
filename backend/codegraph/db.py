"""Neo4j database connection and schema management."""

from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver, Session
import logging

logger = logging.getLogger(__name__)


class CodeGraphDB:
    """Manages Neo4j connection and schema for code graph."""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j",
                 password: str = "password"):
        """
        Initialize Neo4j connection.

        Args:
            uri: Neo4j connection URI
            user: Database username
            password: Database password
        """
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"Connected to Neo4j at {uri}")

    def close(self):
        """Close database connection."""
        if self.driver:
            self.driver.close()
            logger.info("Closed Neo4j connection")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def clear_database(self):
        """Clear all nodes and relationships. Use with caution!"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.warning("Database cleared")

    def delete_nodes_from_file(self, file_path: str):
        """
        Delete all nodes that were defined in a specific file.
        This is useful when re-indexing a file to avoid duplicates.

        Args:
            file_path: Path to the file whose nodes should be deleted
        """
        with self.driver.session() as session:
            # Delete nodes where location starts with the file_path
            # This handles both nodes with location property and relationship locations
            query = """
            MATCH (n)
            WHERE n.location STARTS WITH $file_path
            DETACH DELETE n
            """
            result = session.run(query, {"file_path": file_path})
            summary = result.consume()
            deleted_count = summary.counters.nodes_deleted
            logger.info(f"Deleted {deleted_count} nodes from {file_path}")
            return deleted_count

    def initialize_schema(self):
        """Create indexes and constraints for optimal performance."""
        with self.driver.session() as session:
            constraints_and_indexes = [
                # Unique constraints
                "CREATE CONSTRAINT function_id_unique IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
                "CREATE CONSTRAINT class_id_unique IF NOT EXISTS FOR (c:Class) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT module_id_unique IF NOT EXISTS FOR (m:Module) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT variable_id_unique IF NOT EXISTS FOR (v:Variable) REQUIRE v.id IS UNIQUE",
                "CREATE CONSTRAINT parameter_id_unique IF NOT EXISTS FOR (p:Parameter) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT type_id_unique IF NOT EXISTS FOR (t:Type) REQUIRE t.id IS UNIQUE",

                # Indexes for common queries
                "CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name)",
                "CREATE INDEX function_qualified_idx IF NOT EXISTS FOR (f:Function) ON (f.qualified_name)",
                "CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name)",
                "CREATE INDEX variable_name_idx IF NOT EXISTS FOR (v:Variable) ON (v.name)",
                "CREATE INDEX module_path_idx IF NOT EXISTS FOR (m:Module) ON (m.path)",
            ]

            for query in constraints_and_indexes:
                try:
                    session.run(query)
                    logger.info(f"Executed: {query[:50]}...")
                except Exception as e:
                    logger.warning(f"Schema initialization warning: {e}")

            logger.info("Schema initialized")

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [dict(record) for record in result]

    def create_node(self, label: str, properties: Dict[str, Any]) -> str:
        """
        Create a node with given label and properties.

        Args:
            label: Node label (Function, Class, etc.)
            properties: Node properties

        Returns:
            Node ID
        """
        query = f"CREATE (n:{label} $props) RETURN n.id as id"
        with self.driver.session() as session:
            result = session.run(query, {"props": properties})
            return result.single()["id"]

    def create_relationship(self, from_id: str, to_id: str,
                          rel_type: str, properties: Optional[Dict[str, Any]] = None):
        """
        Create a relationship between two nodes.

        Args:
            from_id: Source node ID
            to_id: Target node ID
            rel_type: Relationship type
            properties: Relationship properties
        """
        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        CREATE (a)-[r:{rel_type}]->(b)
        SET r = $props
        """
        with self.driver.session() as session:
            session.run(query, {
                "from_id": from_id,
                "to_id": to_id,
                "props": properties or {}
            })

    def find_node(self, label: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Find a node by label and properties.

        Args:
            label: Node label
            properties: Properties to match

        Returns:
            Node properties if found, None otherwise
        """
        # Build WHERE clause
        where_clauses = [f"n.{key} = ${key}" for key in properties.keys()]
        where_str = " AND ".join(where_clauses)

        query = f"MATCH (n:{label}) WHERE {where_str} RETURN n"
        with self.driver.session() as session:
            result = session.run(query, properties)
            record = result.single()
            return dict(record["n"]) if record else None

    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        stats = {}

        # Count nodes by label
        for label in ["Function", "Class", "Variable", "Parameter", "Module", "Type"]:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
            with self.driver.session() as session:
                result = session.run(query)
                stats[label] = result.single()["count"]

        # Count relationships
        query = "MATCH ()-[r]->() RETURN count(r) as count"
        with self.driver.session() as session:
            result = session.run(query)
            stats["Relationships"] = result.single()["count"]

        return stats
