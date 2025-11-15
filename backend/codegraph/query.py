"""Query interface for code graph with conservation law support."""

from typing import List, Dict, Any, Optional
from .db import CodeGraphDB
import logging

logger = logging.getLogger(__name__)


class QueryInterface:
    """High-level query interface for the code graph."""

    def __init__(self, db: CodeGraphDB):
        """
        Initialize query interface.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db

    def find_function(self, name: str = None, qualified_name: str = None) -> List[Dict[str, Any]]:
        """
        Find functions by name or qualified name.

        Args:
            name: Simple function name
            qualified_name: Fully qualified name

        Returns:
            List of function nodes
        """
        if qualified_name:
            query = "MATCH (f:Function {qualified_name: $qualified_name}) RETURN f"
            params = {"qualified_name": qualified_name}
        elif name:
            query = "MATCH (f:Function {name: $name}) RETURN f"
            params = {"name": name}
        else:
            query = "MATCH (f:Function) RETURN f LIMIT 100"
            params = {}

        results = self.db.execute_query(query, params)
        return [dict(r["f"]) for r in results]

    def find_callers(self, function_id: str) -> List[Dict[str, Any]]:
        """
        Find all functions that call a given function.

        Args:
            function_id: Target function ID

        Returns:
            List of caller function nodes with call details
        """
        query = """
        MATCH (caller:Function)-[r:CALLS]->(callee:Function {id: $function_id})
        RETURN caller, r.arg_count as arg_count, r.location as location
        """
        results = self.db.execute_query(query, {"function_id": function_id})
        return [
            {
                "caller": dict(r["caller"]),
                "arg_count": r.get("arg_count"),
                "location": r.get("location")
            }
            for r in results
        ]

    def find_callees(self, function_id: str) -> List[Dict[str, Any]]:
        """
        Find all functions called by a given function.

        Args:
            function_id: Source function ID

        Returns:
            List of callee function nodes
        """
        query = """
        MATCH (caller:Function {id: $function_id})-[r:CALLS]->(callee:Function)
        RETURN callee, r.arg_count as arg_count, r.location as location
        """
        results = self.db.execute_query(query, {"function_id": function_id})
        return [
            {
                "callee": dict(r["callee"]),
                "arg_count": r.get("arg_count"),
                "location": r.get("location")
            }
            for r in results
        ]

    def get_function_signature(self, function_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete function signature including parameters.

        Args:
            function_id: Function ID

        Returns:
            Dictionary with function info and parameters
        """
        query = """
        MATCH (f:Function {id: $function_id})
        OPTIONAL MATCH (f)-[r:HAS_PARAMETER]->(p:Parameter)
        WITH f, p, r
        ORDER BY r.position
        RETURN f, collect({param: p, position: r.position}) as parameters
        """
        results = self.db.execute_query(query, {"function_id": function_id})

        if not results:
            return None

        result = results[0]
        return {
            "function": dict(result["f"]),
            "parameters": [
                {
                    "param": dict(p["param"]),
                    "position": p["position"]
                }
                for p in result["parameters"] if p["param"]
            ]
        }

    def find_references(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Find all references to an entity (function, class, variable).

        Args:
            entity_id: Entity ID

        Returns:
            List of referencing nodes
        """
        query = """
        MATCH (source)-[r:REFERENCES]->(target {id: $entity_id})
        RETURN source, type(r) as rel_type, r.location as location
        """
        results = self.db.execute_query(query, {"entity_id": entity_id})
        return [
            {
                "source": dict(r["source"]),
                "rel_type": r["rel_type"],
                "location": r.get("location")
            }
            for r in results
        ]

    def get_class_hierarchy(self, class_id: str) -> Dict[str, Any]:
        """
        Get class inheritance hierarchy.

        Args:
            class_id: Class ID

        Returns:
            Dictionary with base classes and derived classes
        """
        # Get base classes
        base_query = """
        MATCH (c:Class {id: $class_id})-[:INHERITS]->(base:Class)
        RETURN collect(base) as bases
        """
        base_results = self.db.execute_query(base_query, {"class_id": class_id})
        bases = [dict(b) for b in base_results[0]["bases"]] if base_results else []

        # Get derived classes
        derived_query = """
        MATCH (derived:Class)-[:INHERITS]->(c:Class {id: $class_id})
        RETURN collect(derived) as derived
        """
        derived_results = self.db.execute_query(derived_query, {"class_id": class_id})
        derived = [dict(d) for d in derived_results[0]["derived"]] if derived_results else []

        return {
            "bases": bases,
            "derived": derived
        }

    def get_function_dependencies(self, function_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        Get all dependencies of a function (what it calls, what calls it).

        Args:
            function_id: Function ID
            depth: How many levels deep to traverse

        Returns:
            Dictionary with inbound and outbound dependencies
        """
        # Outbound (what this function calls)
        outbound_query = f"""
        MATCH path = (f:Function {{id: $function_id}})-[:CALLS*1..{depth}]->(callee:Function)
        RETURN callee, length(path) as distance
        """
        outbound = self.db.execute_query(outbound_query, {"function_id": function_id})

        # Inbound (what calls this function)
        inbound_query = f"""
        MATCH path = (caller:Function)-[:CALLS*1..{depth}]->(f:Function {{id: $function_id}})
        RETURN caller, length(path) as distance
        """
        inbound = self.db.execute_query(inbound_query, {"function_id": function_id})

        return {
            "outbound": [{"function": dict(r["callee"]), "distance": r["distance"]} for r in outbound],
            "inbound": [{"function": dict(r["caller"]), "distance": r["distance"]} for r in inbound]
        }

    def find_orphaned_nodes(self) -> List[Dict[str, Any]]:
        """
        Find nodes with no relationships (potential orphans).

        Returns:
            List of orphaned nodes
        """
        query = """
        MATCH (n)
        WHERE NOT (n)-[]-()
        RETURN n, labels(n) as labels
        """
        results = self.db.execute_query(query)
        return [
            {
                "node": dict(r["n"]),
                "labels": r["labels"]
            }
            for r in results
        ]

    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Find circular dependencies in the call graph.

        Returns:
            List of cycles (each cycle is a list of function IDs)
        """
        # This is a simplified version - full cycle detection is complex in Cypher
        query = """
        MATCH path = (f:Function)-[:CALLS*]->(f)
        RETURN [node in nodes(path) | node.id] as cycle
        LIMIT 100
        """
        results = self.db.execute_query(query)
        return [r["cycle"] for r in results]

    def get_impact_analysis(self, entity_id: str, change_type: str = "modify") -> Dict[str, Any]:
        """
        Analyze the impact of changing an entity.

        Args:
            entity_id: Entity to change
            change_type: Type of change (modify, delete, rename)

        Returns:
            Impact analysis results
        """
        impact = {
            "entity_id": entity_id,
            "change_type": change_type,
            "affected_callers": [],
            "affected_references": [],
            "cascading_changes": []
        }

        # Find callers (for functions)
        callers = self.find_callers(entity_id)
        if callers:
            impact["affected_callers"] = callers

        # Find references
        references = self.find_references(entity_id)
        if references:
            impact["affected_references"] = references

        # For delete, need to check all relationships
        if change_type == "delete":
            query = """
            MATCH (n {id: $entity_id})-[r]-(connected)
            RETURN type(r) as rel_type, labels(connected) as labels, count(connected) as count
            """
            results = self.db.execute_query(query, {"entity_id": entity_id})
            impact["cascading_changes"] = [dict(r) for r in results]

        return impact

    def search_by_pattern(self, pattern: str, entity_type: str = None) -> List[Dict[str, Any]]:
        """
        Search for entities by name pattern.

        Args:
            pattern: Regex pattern to match
            entity_type: Optional entity type filter (Function, Class, etc.)

        Returns:
            Matching entities
        """
        if entity_type:
            query = f"""
            MATCH (n:{entity_type})
            WHERE n.name =~ $pattern OR n.qualified_name =~ $pattern
            RETURN n, labels(n) as labels
            LIMIT 100
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name =~ $pattern OR n.qualified_name =~ $pattern
            RETURN n, labels(n) as labels
            LIMIT 100
            """

        results = self.db.execute_query(query, {"pattern": f".*{pattern}.*"})
        return [
            {
                "node": dict(r["n"]),
                "labels": r["labels"]
            }
            for r in results
        ]
