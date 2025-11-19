"""Neo4j database connection and schema management."""

from typing import Optional, Dict, Any, List
from neo4j import GraphDatabase, Driver
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

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()

    def clear_database(self):
        """Clear all nodes and relationships. Use with caution!"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.warning("Database cleared")

    def delete_nodes_from_file(self, file_path: str):
        """
        Delete all nodes that were defined under a specific path.
        Works for both individual files and directories because locations
        are stored as absolute file paths with line/column info.

        Args:
            file_path: Path prefix whose nodes should be deleted
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

                # Index for incremental validation
                "CREATE INDEX node_changed_idx IF NOT EXISTS FOR (n:Function) ON (n.changed)",
                "CREATE INDEX class_changed_idx IF NOT EXISTS FOR (c:Class) ON (c.changed)",
                "CREATE INDEX callsite_changed_idx IF NOT EXISTS FOR (cs:CallSite) ON (cs.changed)",
                "CREATE INDEX param_changed_idx IF NOT EXISTS FOR (p:Parameter) ON (p.changed)",

                # Index for snapshots
                "CREATE INDEX node_snapshot_idx IF NOT EXISTS FOR (n:Function) ON (n.snapshot_id)",
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

    def get_all_nodes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return nodes with labels and properties for visualization."""
        query = """
        MATCH (n)
        RETURN n, labels(n) as labels
        LIMIT $limit
        """
        nodes = []
        with self.driver.session() as session:
            results = session.run(query, {"limit": limit})
            for record in results:
                node_props = dict(record["n"])
                nodes.append({
                    "id": node_props.get("id"),
                    "labels": record["labels"],
                    "properties": node_props
                })
        return nodes

    def get_all_edges(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return edge data for visualization."""
        query = """
        MATCH (a)-[r]->(b)
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        LIMIT $limit
        """
        edges = []
        with self.driver.session() as session:
            results = session.run(query, {"limit": limit})
            for record in results:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["rel_type"],
                    "properties": record["props"] or {}
                })
        return edges

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single node with labels."""
        query = "MATCH (n {id: $node_id}) RETURN n, labels(n) as labels LIMIT 1"
        with self.driver.session() as session:
            result = session.run(query, {"node_id": node_id})
            record = result.single()
            if not record:
                return None
            node_props = dict(record["n"])
            return {
                "id": node_props.get("id"),
                "labels": record["labels"],
                "properties": node_props
            }

    def get_node_edges(self, node_id: str) -> List[Dict[str, Any]]:
        """Fetch all edges connected to a node."""
        query = """
        MATCH (a {id: $node_id})-[r]->(b)
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        UNION
        MATCH (a)-[r]->(b {id: $node_id})
        RETURN a.id as source, b.id as target, type(r) as rel_type, properties(r) as props
        """
        edges = []
        with self.driver.session() as session:
            results = session.run(query, {"node_id": node_id})
            for record in results:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["rel_type"],
                    "properties": record["props"] or {}
                })
        return edges

    def get_node_neighborhood(self, node_id: str, depth: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Return nodes and edges within a neighborhood of the target node."""
        node_query = """
        MATCH path = (center {id: $node_id})-[*0..$depth]-(neighbor)
        UNWIND nodes(path) as n
        RETURN DISTINCT n, labels(n) as labels
        """
        edge_query = """
        MATCH path = (center {id: $node_id})-[*1..$depth]-(neighbor)
        UNWIND relationships(path) as r
        RETURN DISTINCT startNode(r).id as source,
                        endNode(r).id as target,
                        type(r) as rel_type,
                        properties(r) as props
        """
        nodes = []
        edges = []
        with self.driver.session() as session:
            for record in session.run(node_query, {"node_id": node_id, "depth": depth}):
                node_props = dict(record["n"])
                nodes.append({
                    "id": node_props.get("id"),
                    "labels": record["labels"],
                    "properties": node_props
                })

            for record in session.run(edge_query, {"node_id": node_id, "depth": depth}):
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["rel_type"],
                    "properties": record["props"] or {}
                })

        return {"nodes": nodes, "edges": edges}

    def search_nodes(self, pattern: str, node_type: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search nodes by name or qualified name."""
        pattern = pattern or ""
        params = {
            "pattern": pattern.lower(),
            "limit": limit
        }
        label = None
        if node_type:
            normalized = node_type.strip()
            if normalized and normalized.replace("_", "").isalnum():
                label = normalized

        if label:
            query = f"""
            MATCH (n:{label})
            WHERE toLower(coalesce(n.name, '')) CONTAINS $pattern
               OR toLower(coalesce(n.qualified_name, '')) CONTAINS $pattern
            RETURN n, labels(n) as labels
            LIMIT $limit
            """
        else:
            query = """
            MATCH (n)
            WHERE toLower(coalesce(n.name, '')) CONTAINS $pattern
               OR toLower(coalesce(n.qualified_name, '')) CONTAINS $pattern
            RETURN n, labels(n) as labels
            LIMIT $limit
            """

        results = []
        with self.driver.session() as session:
            for record in session.run(query, params):
                node_props = dict(record["n"])
                results.append({
                    "id": node_props.get("id"),
                    "labels": record["labels"],
                    "properties": node_props
                })
        return results

    def get_all_functions(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Return paginated functions."""
        query = """
        MATCH (f:Function)
        RETURN f
        ORDER BY f.qualified_name
        SKIP $skip
        LIMIT $limit
        """
        with self.driver.session() as session:
            results = session.run(query, {"skip": skip, "limit": limit})
            return [dict(record["f"]) for record in results]

    def get_function_by_id(self, function_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a function node."""
        query = "MATCH (f:Function {id: $function_id}) RETURN f LIMIT 1"
        with self.driver.session() as session:
            result = session.run(query, {"function_id": function_id})
            record = result.single()
            return dict(record["f"]) if record else None

    def get_function_subgraph(self, function_id: str, depth: int = 1) -> Optional[Dict[str, Any]]:
        """Return nodes/edges surrounding a function."""
        node_query = """
        MATCH path = (f:Function {id: $function_id})-[*0..$depth]-(neighbor)
        UNWIND nodes(path) as n
        RETURN DISTINCT n, labels(n) as labels
        """
        edge_query = """
        MATCH path = (f:Function {id: $function_id})-[*1..$depth]-(neighbor)
        UNWIND relationships(path) as r
        RETURN DISTINCT startNode(r).id as source,
                        endNode(r).id as target,
                        type(r) as rel_type,
                        properties(r) as props
        """
        with self.driver.session() as session:
            nodes = []
            edges = []
            for record in session.run(node_query, {"function_id": function_id, "depth": depth}):
                node_props = dict(record["n"])
                nodes.append({
                    "id": node_props.get("id"),
                    "labels": record["labels"],
                    "properties": node_props
                })
            for record in session.run(edge_query, {"function_id": function_id, "depth": depth}):
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["rel_type"],
                    "properties": record["props"] or {}
                })

        if not nodes:
            return None
        return {"nodes": nodes, "edges": edges}

    def resolve_function_id(self, callee_name: str) -> Optional[str]:
        """
        Attempt to resolve a function ID based on a call-site name.

        Args:
            callee_name: Name captured from the AST call expression.
        """
        if not callee_name:
            return None

        simple_name = callee_name.split('.')[-1]
        qualified_suffix = f".{callee_name}" if '.' in callee_name else f".{simple_name}"
        query = """
        MATCH (f:Function)
        WHERE f.qualified_name = $qualified_name
           OR f.qualified_name ENDS WITH $qualified_suffix
           OR f.name = $simple_name
        WITH f,
             CASE
                 WHEN f.qualified_name = $qualified_name THEN 0
                 WHEN f.qualified_name ENDS WITH $qualified_suffix THEN 1
                 WHEN f.name = $simple_name THEN 2
                 ELSE 3
             END as priority
        RETURN f.id as id
        ORDER BY priority, size(f.qualified_name)
        LIMIT 1
        """
        params = {
            "qualified_name": callee_name,
            "qualified_suffix": qualified_suffix,
            "simple_name": simple_name
        }
        with self.driver.session() as session:
            result = session.run(query, params)
            record = result.single()
            return record["id"] if record else None

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

    # ========== Incremental Validation Support ==========

    def mark_nodes_changed(self, node_ids: List[str]):
        """
        Mark specific nodes as changed for incremental validation.

        Args:
            node_ids: List of node IDs to mark as changed
        """
        if not node_ids:
            return

        query = """
        MATCH (n)
        WHERE n.id IN $node_ids
        SET n.changed = true
        RETURN count(n) as marked
        """
        with self.driver.session() as session:
            result = session.run(query, {"node_ids": node_ids})
            count = result.single()["marked"]
            logger.info(f"Marked {count} nodes as changed")

    def mark_file_nodes_changed(self, file_path: str):
        """
        Mark all nodes from a specific file as changed.

        Args:
            file_path: Path to the file whose nodes should be marked
        """
        query = """
        MATCH (n)
        WHERE n.location STARTS WITH $file_path
        SET n.changed = true
        RETURN count(n) as marked
        """
        with self.driver.session() as session:
            result = session.run(query, {"file_path": file_path})
            count = result.single()["marked"]
            logger.info(f"Marked {count} nodes from {file_path} as changed")
            return count

    def propagate_changed_flag(self) -> int:
        """
        Propagate the 'changed' flag along dependency edges.
        This implements the "semantic light cone" from the theory.

        Returns:
            Number of nodes marked as changed by propagation
        """
        total_propagated = 0

        # Propagation queries - mark dependents of changed nodes
        propagation_queries = [
            # CallSites that call changed functions
            """
            MATCH (f:Function)<-[:CALLS]-(cs:CallSite)
            WHERE f.changed = true AND (cs.changed IS NULL OR cs.changed = false)
            SET cs.changed = true
            RETURN count(cs) as propagated
            """,
            # CallSites that resolve to changed functions
            """
            MATCH (f:Function)<-[:RESOLVES_TO]-(cs:CallSite)
            WHERE f.changed = true AND (cs.changed IS NULL OR cs.changed = false)
            SET cs.changed = true
            RETURN count(cs) as propagated
            """,
            # Functions that call changed functions (via their callsites)
            """
            MATCH (caller:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:CALLS]->(callee:Function)
            WHERE callee.changed = true AND (caller.changed IS NULL OR caller.changed = false)
            SET caller.changed = true
            RETURN count(caller) as propagated
            """,
            # Classes that inherit from changed classes
            """
            MATCH (derived:Class)-[:INHERITS]->(base:Class)
            WHERE base.changed = true AND (derived.changed IS NULL OR derived.changed = false)
            SET derived.changed = true
            RETURN count(derived) as propagated
            """,
            # Functions in changed classes
            """
            MATCH (c:Class)-[:DEFINES]->(f:Function)
            WHERE c.changed = true AND (f.changed IS NULL OR f.changed = false)
            SET f.changed = true
            RETURN count(f) as propagated
            """,
            # Parameters of changed functions
            """
            MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
            WHERE f.changed = true AND (p.changed IS NULL OR p.changed = false)
            SET p.changed = true
            RETURN count(p) as propagated
            """,
            # Modules that import changed modules
            """
            MATCH (importer:Module)-[:IMPORTS]->(imported:Module)
            WHERE imported.changed = true AND (importer.changed IS NULL OR importer.changed = false)
            SET importer.changed = true
            RETURN count(importer) as propagated
            """,
            # Functions/classes in changed modules
            """
            MATCH (m:Module)-[:DECLARES]->(entity)
            WHERE m.changed = true AND (entity.changed IS NULL OR entity.changed = false)
            SET entity.changed = true
            RETURN count(entity) as propagated
            """,
        ]

        with self.driver.session() as session:
            # Run propagation iteratively until no more changes
            iterations = 0
            max_iterations = 10  # Prevent infinite loops

            while iterations < max_iterations:
                iteration_propagated = 0

                for query in propagation_queries:
                    result = session.run(query)
                    count = result.single()["propagated"]
                    iteration_propagated += count

                if iteration_propagated == 0:
                    break

                total_propagated += iteration_propagated
                iterations += 1
                logger.debug(f"Propagation iteration {iterations}: {iteration_propagated} nodes")

        logger.info(f"Propagated changed flag to {total_propagated} nodes in {iterations} iterations")
        return total_propagated

    def clear_changed_flags(self):
        """Clear all 'changed' flags after successful validation."""
        query = """
        MATCH (n)
        WHERE n.changed = true
        REMOVE n.changed
        RETURN count(n) as cleared
        """
        with self.driver.session() as session:
            result = session.run(query)
            count = result.single()["cleared"]
            logger.info(f"Cleared changed flag from {count} nodes")
            return count

    def get_changed_nodes(self) -> List[Dict[str, Any]]:
        """
        Get all nodes marked as changed.

        Returns:
            List of changed nodes with their labels
        """
        query = """
        MATCH (n)
        WHERE n.changed = true
        RETURN n, labels(n) as labels
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [{"node": dict(record["n"]), "labels": record["labels"]} for record in result]

    def get_changed_node_ids(self) -> List[str]:
        """
        Get IDs of all changed nodes.

        Returns:
            List of node IDs
        """
        query = """
        MATCH (n)
        WHERE n.changed = true
        RETURN n.id as id
        """
        with self.driver.session() as session:
            result = session.run(query)
            return [record["id"] for record in result]

    def mark_file_nodes_changed(self, file_path: str) -> int:
        """
        Mark all nodes from a specific file as changed.

        Args:
            file_path: Path of the file whose nodes should be marked

        Returns:
            Number of nodes marked as changed
        """
        query = """
        MATCH (n)
        WHERE n.location STARTS WITH $file_path
        SET n.changed = true
        RETURN count(n) as count
        """
        with self.driver.session() as session:
            result = session.run(query, {"file_path": file_path})
            count = result.single()["count"]
            logger.info(f"Marked {count} nodes from {file_path} as changed")
            return count

    def propagate_changes_to_dependents(self) -> Dict[str, int]:
        """
        Propagate 'changed' marker to all dependent nodes.

        This implements the change propagation algorithm from the paper:
        - Functions that are called by changed call sites
        - Call sites that call changed functions
        - Modules that import changed modules
        - Classes that inherit from changed classes

        Returns:
            Dictionary with counts of propagated changes by type
        """
        counts = {
            "callers": 0,
            "callees": 0,
            "importers": 0,
            "subclasses": 0
        }

        with self.driver.session() as session:
            # Propagate to call sites calling changed functions
            query1 = """
            MATCH (f:Function)<-[:RESOLVES_TO]-(c:CallSite)
            WHERE f.changed = true AND (c.changed IS NULL OR c.changed = false)
            SET c.changed = true
            RETURN count(c) as count
            """
            result = session.run(query1)
            counts["callers"] = result.single()["count"]

            # Propagate to functions called by changed call sites
            query2 = """
            MATCH (c:CallSite)-[:RESOLVES_TO]->(f:Function)
            WHERE c.changed = true AND (f.changed IS NULL OR f.changed = false)
            SET f.changed = true
            RETURN count(f) as count
            """
            result = session.run(query2)
            counts["callees"] = result.single()["count"]

            # Propagate to modules importing changed modules
            query3 = """
            MATCH (m:Module)<-[:IMPORTS]-(importing:Module)
            WHERE m.changed = true AND (importing.changed IS NULL OR importing.changed = false)
            SET importing.changed = true
            RETURN count(importing) as count
            """
            result = session.run(query3)
            counts["importers"] = result.single()["count"]

            # Propagate to subclasses of changed classes
            query4 = """
            MATCH (c:Class)<-[:INHERITS]-(subclass:Class)
            WHERE c.changed = true AND (subclass.changed IS NULL OR subclass.changed = false)
            SET subclass.changed = true
            RETURN count(subclass) as count
            """
            result = session.run(query4)
            counts["subclasses"] = result.single()["count"]

        total = sum(counts.values())
        if total > 0:
            logger.info(f"Propagated changes to {total} dependent nodes: {counts}")

        return counts
