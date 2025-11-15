"""Graph builder to populate Neo4j from parsed entities."""

from typing import Dict, List
from .db import CodeGraphDB
from .parser import Entity, Relationship, FunctionEntity, ClassEntity, VariableEntity, ParameterEntity
import logging

logger = logging.getLogger(__name__)


class GraphBuilder:
    """Builds the code graph in Neo4j from parsed entities and relationships."""

    def __init__(self, db: CodeGraphDB):
        """
        Initialize graph builder.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db
        self.entity_map: Dict[str, str] = {}  # Maps entity IDs to qualified names

    def build_graph(self, entities: Dict[str, Entity], relationships: List[Relationship]):
        """
        Build graph from entities and relationships.

        Args:
            entities: Dictionary of entities keyed by ID
            relationships: List of relationships
        """
        logger.info(f"Building graph with {len(entities)} entities and {len(relationships)} relationships")

        # First pass: Create all nodes
        for entity_id, entity in entities.items():
            self._create_node(entity)
            self.entity_map[entity_id] = entity_id

        # Second pass: Create relationships
        for rel in relationships:
            self._create_relationship(rel, entities)

        logger.info("Graph building complete")

    def _create_node(self, entity: Entity):
        """Create a node in Neo4j from an entity."""
        if isinstance(entity, FunctionEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "signature": entity.signature,
                "visibility": entity.visibility,
                "is_async": entity.is_async,
                "location": entity.location,
            }
            if entity.return_type:
                properties["return_type"] = entity.return_type
            if entity.docstring:
                properties["docstring"] = entity.docstring

            self._create_node_cypher("Function", properties)

        elif isinstance(entity, ClassEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "visibility": entity.visibility,
                "location": entity.location,
            }
            if entity.docstring:
                properties["docstring"] = entity.docstring

            self._create_node_cypher("Class", properties)

        elif isinstance(entity, VariableEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "scope": entity.scope,
                "location": entity.location,
            }
            if entity.type_annotation:
                properties["type_annotation"] = entity.type_annotation

            self._create_node_cypher("Variable", properties)

        elif isinstance(entity, ParameterEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "position": entity.position,
                "kind": entity.kind,
                "location": entity.location,
            }
            if entity.type_annotation:
                properties["type_annotation"] = entity.type_annotation
            if entity.default_value:
                properties["default_value"] = entity.default_value

            self._create_node_cypher("Parameter", properties)

    def _create_node_cypher(self, label: str, properties: Dict):
        """Execute Cypher to create or update a node."""
        # Use MERGE on id to update existing nodes or create new ones
        # This prevents duplicate nodes when re-indexing
        node_id = properties.get("id")
        if not node_id:
            logger.error(f"Cannot create {label} node without id")
            return

        # Build SET clause for all properties except id
        set_props = {k: v for k, v in properties.items() if k != "id"}

        if set_props:
            set_assignments = ", ".join([f"n.{k} = ${k}" for k in set_props.keys()])
            query = f"""
            MERGE (n:{label} {{id: $id}})
            SET {set_assignments}
            """
        else:
            query = f"MERGE (n:{label} {{id: $id}})"

        try:
            self.db.execute_query(query, properties)
        except Exception as e:
            logger.error(f"Failed to create/update {label} node: {e}")

    def _create_relationship(self, rel: Relationship, entities: Dict[str, Entity]):
        """Create a relationship in Neo4j."""
        # Handle unresolved CALLS relationships
        if rel.to_id.startswith("unresolved:"):
            # Try to resolve the callee
            callee_name = rel.to_id.replace("unresolved:", "")
            resolved_id = self._resolve_function_name(callee_name, entities)

            if resolved_id:
                rel.to_id = resolved_id
            else:
                # Skip unresolved calls for now
                logger.debug(f"Skipping unresolved call to {callee_name}")
                return

        # Check both nodes exist
        if rel.from_id not in entities or rel.to_id not in entities:
            logger.debug(f"Skipping relationship: missing nodes {rel.from_id} or {rel.to_id}")
            return

        # Create relationship
        prop_str = ""
        if rel.properties:
            prop_assignments = ", ".join([f"{k}: ${k}" for k in rel.properties.keys()])
            prop_str = f"SET r = {{{prop_assignments}}}"

        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        CREATE (a)-[r:{rel.rel_type}]->(b)
        {prop_str}
        """

        params = {
            "from_id": rel.from_id,
            "to_id": rel.to_id,
            **rel.properties
        }

        try:
            self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to create {rel.rel_type} relationship: {e}")

    def _resolve_function_name(self, name: str, entities: Dict[str, Entity]) -> str:
        """
        Try to resolve a function name to an entity ID.

        Args:
            name: Function name (simple or qualified)
            entities: All entities

        Returns:
            Entity ID if found, empty string otherwise
        """
        # Try to find function by name
        for entity_id, entity in entities.items():
            if isinstance(entity, FunctionEntity):
                # Match simple name or qualified name
                if entity.name == name or entity.qualified_name.endswith(f".{name}"):
                    return entity_id

        return ""

    def clear_graph(self):
        """Clear all data from the graph."""
        self.db.clear_database()
        self.entity_map = {}
        logger.info("Graph cleared")
