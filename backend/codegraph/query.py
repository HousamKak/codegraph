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
            List of caller function nodes with call details from CallSite
        """
        query = """
        MATCH (caller:Function)-[:HAS_CALLSITE]->(cs:CallSite)-[:RESOLVES_TO]->(callee:Function {id: $function_id})
        RETURN caller, cs.arg_count as arg_count, cs.location as location, cs.lineno as lineno, cs.col_offset as col_offset
        """
        results = self.db.execute_query(query, {"function_id": function_id})
        return [
            {
                "caller": dict(r["caller"]),
                "arg_count": r.get("arg_count"),
                "location": r.get("location"),
                "lineno": r.get("lineno"),
                "col_offset": r.get("col_offset")
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
        MATCH (caller:Function {id: $function_id})-[:HAS_CALLSITE]->(cs:CallSite)-[r:RESOLVES_TO]->(callee:Function)
        RETURN callee, cs.arg_count as arg_count, cs.location as location
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

    def get_callers(self, function_id: str) -> List[Dict[str, Any]]:
        """Alias for backwards compatibility with API layer."""
        return self.find_callers(function_id)

    def get_callees(self, function_id: str) -> List[Dict[str, Any]]:
        """Alias for backwards compatibility with API layer."""
        return self.find_callees(function_id)

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
        # Pattern: Function -[:HAS_CALLSITE]-> CallSite -[:RESOLVES_TO]-> Function (repeated)
        outbound_query = f"""
        MATCH path = (f:Function {{id: $function_id}})-[:HAS_CALLSITE|RESOLVES_TO*1..{depth*2}]->(callee:Function)
        WHERE all(r in relationships(path) WHERE type(r) IN ['HAS_CALLSITE', 'RESOLVES_TO'])
        RETURN DISTINCT callee, length([r in relationships(path) WHERE type(r) = 'RESOLVES_TO']) as distance
        """
        outbound = self.db.execute_query(outbound_query, {"function_id": function_id})

        # Inbound (what calls this function)
        inbound_query = f"""
        MATCH path = (caller:Function)-[:HAS_CALLSITE|RESOLVES_TO*1..{depth*2}]->(f:Function {{id: $function_id}})
        WHERE all(r in relationships(path) WHERE type(r) IN ['HAS_CALLSITE', 'RESOLVES_TO'])
        RETURN DISTINCT caller, length([r in relationships(path) WHERE type(r) = 'RESOLVES_TO']) as distance
        """
        inbound = self.db.execute_query(inbound_query, {"function_id": function_id})

        return {
            "outbound": [{"function": dict(r["callee"]), "distance": r["distance"]} for r in outbound],
            "inbound": [{"function": dict(r["caller"]), "distance": r["distance"]} for r in inbound]
        }

    def get_dependencies(self, function_id: str, depth: int = 1) -> Dict[str, Any]:
        """Alias to support existing API surface."""
        return self.get_function_dependencies(function_id, depth=depth)

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
        # Pattern: Function -[:HAS_CALLSITE]-> CallSite -[:RESOLVES_TO]-> Function (cycle)
        query = """
        MATCH path = (f:Function)-[:HAS_CALLSITE|RESOLVES_TO*]->(f)
        WHERE all(r in relationships(path) WHERE type(r) IN ['HAS_CALLSITE', 'RESOLVES_TO'])
        AND length(path) > 0
        RETURN [node in nodes(path) WHERE 'Function' IN labels(node) | node.id] as cycle
        LIMIT 100
        """
        results = self.db.execute_query(query)
        return [r["cycle"] for r in results]

    def find_circular_inheritance(self) -> List[List[str]]:
        """
        Find circular inheritance in class hierarchy.

        Returns:
            List of cycles (each cycle is a list of class IDs)
        """
        query = """
        MATCH path = (c:Class)-[:INHERITS*]->(c)
        RETURN [node in nodes(path) | node.qualified_name] as cycle
        LIMIT 100
        """
        results = self.db.execute_query(query)
        return [r["cycle"] for r in results]

    def find_diamond_inheritance(self) -> List[Dict[str, Any]]:
        """
        Find diamond inheritance patterns (class inherits from same base via multiple paths).

        Returns:
            List of diamond patterns with class and common base
        """
        query = """
        MATCH (c:Class)-[:INHERITS*2..]->(base:Class)
        WITH c, base, count(*) as path_count
        WHERE path_count > 1
        RETURN c.qualified_name as class, base.qualified_name as base, path_count
        """
        results = self.db.execute_query(query)
        return [
            {
                "class": r["class"],
                "base": r["base"],
                "path_count": r["path_count"]
            }
            for r in results
        ]

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
