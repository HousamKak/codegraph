"""Graph builder to populate Neo4j from parsed entities."""

from typing import Dict, List
from .db import CodeGraphDB
from .parser import (
    Entity, Relationship, FunctionEntity, ClassEntity, VariableEntity,
    ParameterEntity, ModuleEntity, CallSiteEntity, TypeEntity, DecoratorEntity,
    UnresolvedReferenceEntity
)
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
                "is_generator": entity.is_generator,
                "is_staticmethod": entity.is_staticmethod,
                "is_classmethod": entity.is_classmethod,
                "is_property": entity.is_property,
                "location": entity.location,
            }
            if entity.return_type:
                properties["return_type"] = entity.return_type
            if entity.docstring:
                properties["docstring"] = entity.docstring
            if entity.decorators:
                properties["decorators"] = entity.decorators

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
            if entity.decorators:
                properties["decorators"] = entity.decorators

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
            if entity.inferred_types:
                properties["inferred_types"] = entity.inferred_types

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

        elif isinstance(entity, ModuleEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "qualified_name": entity.qualified_name,
                "path": entity.path,
                "location": entity.location,
                "is_external": entity.is_external,
            }
            if entity.package:
                properties["package"] = entity.package
            if entity.docstring:
                properties["docstring"] = entity.docstring

            self._create_node_cypher("Module", properties)

        elif isinstance(entity, CallSiteEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "caller_id": entity.caller_id,
                "arg_count": entity.arg_count,
                "has_args": entity.has_args,
                "has_kwargs": entity.has_kwargs,
                "lineno": entity.lineno,
                "col_offset": entity.col_offset,
                "location": entity.location,
            }
            if entity.arg_types:
                properties["arg_types"] = entity.arg_types

            self._create_node_cypher("CallSite", properties)

        elif isinstance(entity, TypeEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "module": entity.module,
                "kind": entity.kind,
                "location": entity.location,
            }
            if entity.base_types:
                properties["base_types"] = entity.base_types

            self._create_node_cypher("Type", properties)

        elif isinstance(entity, DecoratorEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "location": entity.location,
                "target_id": entity.target_id,
                "target_type": entity.target_type,
            }
            self._create_node_cypher("Decorator", properties)
        elif isinstance(entity, UnresolvedReferenceEntity):
            properties = {
                "id": entity.id,
                "name": entity.name,
                "location": entity.location,
                "reference_kind": entity.reference_kind,
                "source_id": entity.source_id,
            }
            self._create_node_cypher("Unresolved", properties)

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
        if rel.rel_type == "CALLS_UNRESOLVED" and rel.to_id.startswith("unresolved:"):
            # Try to resolve the callee
            callee_name = rel.to_id.replace("unresolved:", "")
            resolved_id = self._resolve_function_name(callee_name, entities)

            if resolved_id:
                # Create CALLS relationship
                self._create_resolved_call(rel.from_id, resolved_id, callee_name, "resolved", rel.properties)
            else:
                # Create unresolved call marker
                self._create_resolved_call(rel.from_id, None, callee_name, "unresolved", rel.properties)
            return

        # Create relationship (using MERGE to prevent duplicates)
        prop_str = ""
        if rel.properties:
            prop_assignments = ", ".join([f"r.{k} = ${k}" for k in rel.properties.keys()])
            prop_str = f"SET {prop_assignments}"

        query = f"""
        MATCH (a {{id: $from_id}}), (b {{id: $to_id}})
        MERGE (a)-[r:{rel.rel_type}]->(b)
        {prop_str}
        """

        params = {
            "from_id": rel.from_id,
            "to_id": rel.to_id,
            **(rel.properties or {})
        }

        try:
            self.db.execute_query(query, params)
        except Exception as e:
            logger.error(f"Failed to create {rel.rel_type} relationship: {e}")

    def _create_resolved_call(self, callsite_id: str, resolved_id: str, callee_name: str,
                              status: str, properties: Dict):
        """Create CALLS and RESOLVES_TO relationships for a call site."""
        if resolved_id:
            # Create CALLS relationship (CallSite -> Function)
            calls_query = """
            MATCH (cs {id: $callsite_id}), (f {id: $resolved_id})
            MERGE (cs)-[r:CALLS]->(f)
            SET r.callee_name = $callee_name
            """
            try:
                self.db.execute_query(calls_query, {
                    "callsite_id": callsite_id,
                    "resolved_id": resolved_id,
                    "callee_name": callee_name
                })
            except Exception as e:
                logger.error(f"Failed to create CALLS relationship: {e}")

            # Create RESOLVES_TO relationship (CallSite -> Function) with resolution metadata
            resolves_query = """
            MATCH (cs {id: $callsite_id}), (f {id: $resolved_id})
            MERGE (cs)-[r:RESOLVES_TO]->(f)
            SET r.resolution_status = $status,
                r.callee_name = $callee_name
            """
            try:
                self.db.execute_query(resolves_query, {
                    "callsite_id": callsite_id,
                    "resolved_id": resolved_id,
                    "status": status,
                    "callee_name": callee_name
                })
            except Exception as e:
                logger.error(f"Failed to create RESOLVES_TO relationship: {e}")
        else:
            # Mark as unresolved - create a marker on the CallSite node
            unresolved_query = """
            MATCH (cs {id: $callsite_id})
            SET cs.resolution_status = 'unresolved',
                cs.unresolved_callee = $callee_name
            """
            try:
                self.db.execute_query(unresolved_query, {
                    "callsite_id": callsite_id,
                    "callee_name": callee_name
                })
            except Exception as e:
                logger.error(f"Failed to mark unresolved call: {e}")

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

        resolved = self.db.resolve_function_id(name)
        return resolved or ""

    def clear_graph(self):
        """Clear all data from the graph."""
        self.db.clear_database()
        self.entity_map = {}
        logger.info("Graph cleared")
