"""Conservation law validators for code graph integrity."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from .db import CodeGraphDB
from .query import QueryInterface
import logging
import subprocess
import json
import os

logger = logging.getLogger(__name__)


class ViolationType(Enum):
    """Types of conservation law violations."""
    SIGNATURE_MISMATCH = "signature_mismatch"
    REFERENCE_BROKEN = "reference_broken"
    DATA_FLOW_INVALID = "data_flow_invalid"
    STRUCTURAL_INVALID = "structural_invalid"


@dataclass
class Violation:
    """Represents a conservation law violation with detailed location info."""
    violation_type: ViolationType
    severity: str  # "error", "warning"
    entity_id: str
    message: str
    details: Dict[str, Any]
    suggested_fix: Optional[str] = None
    # Enhanced location information
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    # Change tracking
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    # Code context
    code_snippet: Optional[str] = None  # The actual code at the location


class ConservationValidator:
    """Validates the 4 conservation laws in the code graph."""

    # Decorators that transform function signatures
    # These functions should be excluded from signature validation
    SIGNATURE_TRANSFORMING_DECORATORS = {
        'click.group',
        'click.command',
        'click.option',
        'click.argument',
        'property',
        'staticmethod',
        'classmethod',
        'app.list_tools',  # MCP decorators
        'app.call_tool',
        'app.route',  # Flask/FastAPI routes
        'api.get',
        'api.post',
        'dataclass',  # May add __init__ with different signature
    }

    def __init__(self, db: CodeGraphDB):
        """
        Initialize validator.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db
        self.query = QueryInterface(db)
        self._last_report: Optional[Dict[str, Any]] = None

    def _has_transforming_decorator(self, func: Dict[str, Any]) -> bool:
        """
        Check if a function has decorators that transform its signature.

        Args:
            func: Function node dictionary

        Returns:
            True if function has signature-transforming decorators
        """
        # Check if function name or qualified name contains decorator patterns
        func_name = func.get("qualified_name", func.get("name", ""))

        # Check for decorator hints in the qualified name path
        # e.g., if function is in a file that uses Click, and name matches patterns
        if any(pattern in func_name for pattern in ['cli.', 'command']):
            # Likely a Click command
            return True

        # TODO: Once parser tracks decorators explicitly, check for decorator nodes
        # For now, use heuristics based on function names and patterns

        return False

    def _extract_location(self, node: Dict[str, Any]) -> Dict[str, Optional[Any]]:
        """
        Extract location information from a node.

        Args:
            node: Node properties dictionary

        Returns:
            Dictionary with file_path, line_number, column_number
        """
        return {
            "file_path": node.get("file_path"),
            "line_number": node.get("line_number"),
            "column_number": node.get("column_number", 0)
        }

    def _parse_location_string(self, location: str) -> Dict[str, Optional[Any]]:
        """
        Parse location string in format 'file:line:column'.

        Args:
            location: Location string (e.g., '/path/to/file.py:42:12')

        Returns:
            Dictionary with file_path, line_number, column_number
        """
        if not location or location == "unknown":
            return {"file_path": None, "line_number": None, "column_number": None}

        try:
            parts = location.rsplit(':', 2)
            if len(parts) == 3:
                file_path, line_str, col_str = parts
                return {
                    "file_path": file_path,
                    "line_number": int(line_str),
                    "column_number": int(col_str)
                }
            elif len(parts) == 2:
                file_path, line_str = parts
                return {
                    "file_path": file_path,
                    "line_number": int(line_str),
                    "column_number": 0
                }
            else:
                return {"file_path": location, "line_number": None, "column_number": None}
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse location '{location}': {e}")
            return {"file_path": None, "line_number": None, "column_number": None}

    def _get_code_snippet(self, file_path: str, line_number: int, context_lines: int = 2) -> Optional[str]:
        """
        Get code snippet from file at specified line with context.

        Args:
            file_path: Path to source file
            line_number: Line number (1-indexed)
            context_lines: Number of context lines before/after

        Returns:
            Code snippet or None if file not found
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            snippet_lines = []
            for i in range(start, end):
                prefix = ">>> " if i == line_number - 1 else "    "
                snippet_lines.append(f"{prefix}{i+1:4d} | {lines[i].rstrip()}")

            return "\n".join(snippet_lines)

        except (FileNotFoundError, IOError) as e:
            logger.warning(f"Could not read file {file_path}: {e}")
            return None

    def validate_all(self, include_pyright: bool = False) -> List[Violation]:
        """
        Run all conservation law validators.

        Args:
            include_pyright: Whether to run pyright for deep type checking

        Returns:
            List of violations found
        """
        violations = []

        logger.info("Running conservation law validation...")

        law_map = self._collect_law_violations(include_pyright=include_pyright)
        for law_violations in law_map.values():
            violations.extend(law_violations)

        logger.info(f"Validation complete: {len(violations)} violations found")

        return violations

    def validate_signature_conservation(self) -> List[Violation]:
        """
        LAW 1: SIGNATURE CONSERVATION
        Function signature (params + return type + visibility) must match all use sites.

        Checks:
        - All call sites provide correct number of arguments
        - Parameter types match at call sites
        - Visibility rules are respected (no calls to private from outside)

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating signature conservation...")

        # Get all functions
        query = "MATCH (f:Function) RETURN f"
        functions = self.db.execute_query(query)

        for func_record in functions:
            func = dict(func_record["f"])
            func_id = func["id"]

            # Skip functions with signature-transforming decorators
            if self._has_transforming_decorator(func):
                logger.debug(f"Skipping signature validation for decorated function: {func.get('name')}")
                continue

            # Get function parameters
            sig_info = self.query.get_function_signature(func_id)
            if not sig_info:
                continue

            params = sig_info["parameters"]

            # Adjust for self/cls parameters based on decorators
            # For instance methods (has 'self'), callers don't pass it
            # For classmethods (has 'cls'), callers don't pass it
            # For staticmethods, count all params
            params_to_check = params
            if func.get("is_classmethod") or func.get("is_staticmethod") or func.get("is_property"):
                # Skip first parameter (cls for classmethod, self for property)
                # staticmethod shouldn't have self/cls, but check anyway
                if params and params[0].get("param", {}).get("name") in ["self", "cls"]:
                    params_to_check = params[1:]
            elif params and params[0].get("param", {}).get("name") == "self":
                # Instance method - skip self parameter
                params_to_check = params[1:]

            total_params = len(params_to_check)

            # Count required parameters (those without defaults)
            required_params = sum(1 for p in params_to_check if not p.get("param", {}).get("default_value"))

            # Check all callers
            callers = self.query.find_callers(func_id)

            for caller_info in callers:
                caller = caller_info["caller"]
                arg_count = caller_info.get("arg_count")
                location = caller_info.get("location", "unknown")

                # Check arity: arg_count must be between required_params and total_params
                if arg_count is not None:
                    if arg_count < required_params or arg_count > total_params:
                        # Parse location string from relationship
                        loc_info = self._parse_location_string(location)

                        # Get code snippet if location is available
                        code_snippet = None
                        if loc_info["file_path"] and loc_info["line_number"]:
                            code_snippet = self._get_code_snippet(
                                loc_info["file_path"],
                                loc_info["line_number"]
                            )

                        # Build helpful error message
                        if required_params == total_params:
                            expected_msg = f"{required_params} argument{'s' if required_params != 1 else ''}"
                        else:
                            expected_msg = f"{required_params}-{total_params} arguments"

                        violations.append(Violation(
                            violation_type=ViolationType.SIGNATURE_MISMATCH,
                            severity="error",
                            entity_id=func_id,
                            message=f"Function {func['name']} expects {expected_msg} but is called with {arg_count}",
                            details={
                                "function": func["qualified_name"],
                                "required_params": required_params,
                                "total_params": total_params,
                                "actual_args": arg_count,
                                "caller": caller["qualified_name"],
                                "location": location
                            },
                            suggested_fix=f"Update call at {location} to provide {expected_msg}",
                            file_path=loc_info["file_path"],
                            line_number=loc_info["line_number"],
                            column_number=loc_info["column_number"],
                            old_value=arg_count,
                            new_value=required_params if arg_count < required_params else total_params,
                            code_snippet=code_snippet
                        ))

            # Check visibility violations
            if func.get("visibility") == "private":
                # Private functions should only be called from same module
                func_module = func["qualified_name"].rsplit(".", 1)[0] if "." in func["qualified_name"] else ""

                for caller_info in callers:
                    caller = caller_info["caller"]
                    caller_module = caller["qualified_name"].rsplit(".", 1)[0] if "." in caller["qualified_name"] else ""

                    if caller_module != func_module:
                        # Extract location info
                        loc_info = self._extract_location(caller)

                        # Get code snippet
                        code_snippet = None
                        if loc_info["file_path"] and loc_info["line_number"]:
                            code_snippet = self._get_code_snippet(
                                loc_info["file_path"],
                                loc_info["line_number"]
                            )

                        violations.append(Violation(
                            violation_type=ViolationType.SIGNATURE_MISMATCH,
                            severity="warning",
                            entity_id=func_id,
                            message=f"Private function {func['name']} called from different module",
                            details={
                                "function": func["qualified_name"],
                                "caller": caller["qualified_name"],
                                "function_module": func_module,
                                "caller_module": caller_module
                            },
                            suggested_fix=f"Make {func['name']} public or move call to same module",
                            file_path=loc_info["file_path"],
                            line_number=loc_info["line_number"],
                            column_number=loc_info["column_number"],
                            code_snippet=code_snippet
                        ))

        logger.info(f"Signature conservation: {len(violations)} violations")
        return violations

    def validate_reference_integrity(self) -> List[Violation]:
        """
        LAW 2: REFERENCE INTEGRITY
        All identifiers must resolve to valid, accessible entities.

        Checks:
        - No dangling references
        - All referenced entities exist
        - Scope rules are respected
        - No references to deleted entities

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating reference integrity...")

        # Check for orphaned nodes (nodes with no connections)
        orphans = self.query.find_orphaned_nodes()

        for orphan in orphans:
            node = orphan["node"]
            labels = orphan["labels"]

            # Parameters and types can be orphaned temporarily during parsing
            if "Parameter" not in labels and "Type" not in labels:
                violations.append(Violation(
                    violation_type=ViolationType.REFERENCE_BROKEN,
                    severity="warning",
                    entity_id=node.get("id", "unknown"),
                    message=f"Orphaned {labels[0]} node: {node.get('name', 'unknown')}",
                    details={
                        "node": node,
                        "labels": labels
                    },
                    suggested_fix="Remove orphaned node or establish proper relationships"
                ))

        # Check for broken CALLS relationships (calls to non-existent functions)
        query = """
        MATCH (caller:Function)-[r:CALLS]->(callee)
        WHERE callee.id IS NULL
        RETURN caller, r, properties(r) as props
        """
        broken_calls = self.db.execute_query(query)

        for record in broken_calls:
            caller = dict(record["caller"])
            props = record["props"]

            # Extract location info
            loc_info = self._extract_location(caller)

            # Get code snippet
            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(
                    loc_info["file_path"],
                    loc_info["line_number"]
                )

            callee_name = props.get("callee_name", "unknown")

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=caller["id"],
                message=f"Call to non-existent function: {callee_name}",
                details={
                    "caller": caller["qualified_name"],
                    "callee_name": callee_name,
                    "location": props.get("location")
                },
                suggested_fix="Ensure called function exists or remove the call",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                code_snippet=code_snippet
            ))

        # Check that all CallSites have exactly one RESOLVES_TO target (R law core check)
        query = """
        MATCH (cs:CallSite)
        WHERE cs.resolution_status IS NULL OR cs.resolution_status <> 'unresolved'
        OPTIONAL MATCH (cs)-[:RESOLVES_TO]->(f:Function)
        WITH cs, count(f) as target_count
        WHERE target_count <> 1
        RETURN cs, target_count
        """
        bad_resolutions = self.db.execute_query(query)

        for record in bad_resolutions:
            cs = dict(record["cs"])
            target_count = record["target_count"]

            loc_info = self._parse_location_string(cs.get("location", ""))

            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(loc_info["file_path"], loc_info["line_number"])

            if target_count == 0:
                message = f"CallSite {cs.get('name')} has no RESOLVES_TO target"
            else:
                message = f"CallSite {cs.get('name')} resolves to {target_count} targets (ambiguous)"

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=cs["id"],
                message=message,
                details={
                    "callsite": cs.get("name"),
                    "target_count": target_count,
                    "location": cs.get("location")
                },
                suggested_fix="Ensure each call resolves to exactly one function",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                code_snippet=code_snippet
            ))

        # Check for unresolved call sites (marked as unresolved)
        query = """
        MATCH (cs:CallSite)
        WHERE cs.resolution_status = 'unresolved'
        RETURN cs
        """
        unresolved = self.db.execute_query(query)

        for record in unresolved:
            cs = dict(record["cs"])
            loc_info = self._parse_location_string(cs.get("location", ""))

            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(loc_info["file_path"], loc_info["line_number"])

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=cs["id"],
                message=f"Unresolved call to: {cs.get('unresolved_callee', 'unknown')}",
                details={
                    "callsite": cs.get("name"),
                    "callee_name": cs.get("unresolved_callee"),
                    "location": cs.get("location")
                },
                suggested_fix="Ensure the called function exists and is in scope",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                code_snippet=code_snippet
            ))

        # Check for broken import references
        query = """
        MATCH (m:Module)-[:IMPORTS]->(target:Module)
        WHERE target.is_external = true
        RETURN m, target
        LIMIT 100
        """
        # Note: External imports are expected, so this is informational only
        # We could add stricter checking if desired

        # Check for dangling REFERENCES edges
        query = """
        MATCH (source)-[r:REFERENCES]->(target)
        WHERE target.id IS NULL
        RETURN source, properties(r) as props
        LIMIT 100
        """
        dangling_refs = self.db.execute_query(query)

        for record in dangling_refs:
            source = dict(record["source"])
            props = record["props"]

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=source.get("id", "unknown"),
                message=f"Dangling reference from {source.get('name', 'unknown')}",
                details={
                    "source": source.get("qualified_name", source.get("name")),
                    "reference_type": props.get("access_type"),
                    "location": props.get("location")
                },
                suggested_fix="Remove dangling reference or create the target entity"
            ))

        # Check unresolved reference nodes created during parsing
        query = """
        MATCH (u:Unresolved)
        RETURN u
        """
        unresolved_nodes = self.db.execute_query(query)

        for record in unresolved_nodes:
            unresolved = dict(record["u"])
            loc_info = self._parse_location_string(unresolved.get("location", ""))

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=unresolved.get("id"),
                message=f"Unresolved {unresolved.get('reference_kind', 'reference')} to '{unresolved.get('name')}'",
                details={
                    "name": unresolved.get("name"),
                    "reference_kind": unresolved.get("reference_kind"),
                    "source": unresolved.get("source_id")
                },
                suggested_fix="Ensure the referenced identifier exists and is in scope",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"]
            ))

        logger.info(f"Reference integrity: {len(violations)} violations")
        return violations

    def validate_data_flow_consistency(self) -> List[Violation]:
        """
        LAW 3: DATA FLOW CONSISTENCY (T Law)
        Types/values flowing through edges must be compatible.

        Checks:
        - Type annotations are consistent
        - Return types match usage
        - Parameter types match arguments (when annotated)
        - Type compatibility across edges

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating data flow consistency (T law)...")

        # 1. Check for missing type annotations (warnings)
        violations.extend(self._check_missing_type_annotations())

        # 2. Check type compatibility at call sites
        violations.extend(self._check_call_type_compatibility())

        # 3. Check return type consistency
        violations.extend(self._check_return_type_consistency())

        # 4. Check IS_SUBTYPE_OF relationship validity
        violations.extend(self._check_subtype_relationships())

        # 5. Check variable assignment type compatibility
        violations.extend(self._check_variable_type_compatibility())

        logger.info(f"Data flow consistency: {len(violations)} violations")
        return violations

    def _check_missing_type_annotations(self) -> List[Violation]:
        """Check for missing type annotations on parameters and return types."""
        violations = []

        # Check parameters missing type annotations
        query = """
        MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
        WHERE p.type_annotation IS NULL
          AND NOT p.name IN ['self', 'cls']
        RETURN f, p
        """
        untyped_params = self.db.execute_query(query)

        for record in untyped_params:
            func = dict(record["f"])
            param = dict(record["p"])

            loc_info = self._extract_location(func)
            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(loc_info["file_path"], loc_info["line_number"])

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=param["id"],
                message=f"Parameter {param['name']} in {func['name']} missing type annotation",
                details={
                    "function": func["qualified_name"],
                    "parameter": param["name"],
                    "position": param.get("position")
                },
                suggested_fix=f"Add type annotation to parameter {param['name']}",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                code_snippet=code_snippet
            ))

        # Check functions missing return type annotations
        query = """
        MATCH (f:Function)
        WHERE f.return_type IS NULL
          AND NOT f.name STARTS WITH '_'
          AND NOT f.name = '__init__'
        RETURN f
        """
        untyped_functions = self.db.execute_query(query)

        for record in untyped_functions:
            func = dict(record["f"])

            loc_info = self._extract_location(func)

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=func["id"],
                message=f"Function {func['name']} missing return type annotation",
                details={"function": func["qualified_name"]},
                suggested_fix="Add return type annotation",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"]
            ))

        return violations

    def _check_call_type_compatibility(self) -> List[Violation]:
        """
        Check that argument types at call sites are compatible with parameter types.
        This is the core T law check: Γ ⊢ f(a₁,...,aₙ) requires σᵢ ≤ τᵢ
        """
        violations = []

        # Get call sites with typed parameters
        query = """
        MATCH (cs:CallSite)-[:CALLS]->(f:Function)-[:HAS_PARAMETER]->(p:Parameter)
        WHERE p.type_annotation IS NOT NULL
        OPTIONAL MATCH (p)-[:HAS_TYPE]->(pt:Type)
        WITH cs, f, p, pt
        ORDER BY p.position
        RETURN cs, f, collect({param: p, type: pt}) as params
        """
        results = self.db.execute_query(query)

        for record in results:
            cs = dict(record["cs"])
            func = dict(record["f"])
            params = record["params"]

            # Get argument types from call site if available
            # This requires the parser to track argument types
            arg_types = cs.get("arg_types", [])

            if not arg_types:
                continue  # Can't check without argument type info

            for i, param_info in enumerate(params):
                if i >= len(arg_types):
                    break

                param = param_info.get("param", {})
                param_type = param_info.get("type", {})

                if not param_type:
                    continue

                arg_type = arg_types[i]
                if not arg_type:
                    continue
                expected_type = param_type.get("name", param.get("type_annotation", ""))

                # Check compatibility
                if arg_type and expected_type:
                    if not self._types_compatible(arg_type, expected_type):
                        loc_info = self._parse_location_string(cs.get("location", ""))

                        violations.append(Violation(
                            violation_type=ViolationType.DATA_FLOW_INVALID,
                            severity="error",
                            entity_id=cs["id"],
                            message=f"Type mismatch: argument {i+1} is '{arg_type}' but parameter '{param.get('name')}' expects '{expected_type}'",
                            details={
                                "callsite": cs.get("name"),
                                "function": func.get("qualified_name"),
                                "parameter": param.get("name"),
                                "position": i,
                                "arg_type": arg_type,
                                "expected_type": expected_type
                            },
                            suggested_fix=f"Convert argument to {expected_type} or update parameter type",
                            file_path=loc_info["file_path"],
                            line_number=loc_info["line_number"],
                            column_number=loc_info["column_number"]
                        ))

        return violations

    def _check_return_type_consistency(self) -> List[Violation]:
        """
        Check that functions with RETURNS_TYPE edges are consistent.
        """
        violations = []

        # Check functions with multiple return types
        query = """
        MATCH (f:Function)-[:RETURNS_TYPE]->(t:Type)
        WITH f, collect(t) as types
        WHERE size(types) > 1
        RETURN f, types
        """
        results = self.db.execute_query(query)

        for record in results:
            func = dict(record["f"])
            types = [dict(t) for t in record["types"]]

            type_names = [t.get("name", "unknown") for t in types]

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=func["id"],
                message=f"Function {func['name']} has multiple return types: {', '.join(type_names)}",
                details={
                    "function": func["qualified_name"],
                    "types": type_names
                },
                suggested_fix="Unify return types or use Union type"
            ))

        # Check that declared return type matches RETURNS_TYPE edge
        query = """
        MATCH (f:Function)
        WHERE f.return_type IS NOT NULL
        OPTIONAL MATCH (f)-[:RETURNS_TYPE]->(t:Type)
        WITH f, t
        WHERE t IS NULL
        RETURN f
        """
        missing_edges = self.db.execute_query(query)

        for record in missing_edges:
            func = dict(record["f"])

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=func["id"],
                message=f"Function {func['name']} has return_type annotation but no RETURNS_TYPE edge",
                details={
                    "function": func["qualified_name"],
                    "declared_type": func.get("return_type")
                },
                suggested_fix="Ensure Type node exists and is linked"
            ))

        return violations

    def _check_subtype_relationships(self) -> List[Violation]:
        """
        Check that IS_SUBTYPE_OF relationships form a valid hierarchy.
        """
        violations = []

        # Check for cycles in subtype relationships
        query = """
        MATCH (t:Type)
        MATCH path = (t)-[:IS_SUBTYPE_OF*1..]->(t)
        RETURN t, [n IN nodes(path) | n.name] as cycle
        LIMIT 10
        """
        cycles = self.db.execute_query(query)

        for record in cycles:
            type_node = dict(record["t"])
            cycle = record["cycle"]

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="error",
                entity_id=type_node.get("id", "unknown"),
                message=f"Circular subtype relationship: {' -> '.join(cycle)}",
                details={"cycle": cycle},
                suggested_fix="Remove circular subtype relationship"
            ))

        # Check that subtypes have compatible structures
        query = """
        MATCH (child:Type)-[:IS_SUBTYPE_OF]->(parent:Type)
        WHERE child.kind <> parent.kind
          AND NOT parent.kind IN ['class', 'generic']
        RETURN child, parent
        """
        incompatible = self.db.execute_query(query)

        for record in incompatible:
            child = dict(record["child"])
            parent = dict(record["parent"])

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=child.get("id", "unknown"),
                message=f"Type {child.get('name')} (kind: {child.get('kind')}) cannot be subtype of {parent.get('name')} (kind: {parent.get('kind')})",
                details={
                    "child": child.get("name"),
                    "child_kind": child.get("kind"),
                    "parent": parent.get("name"),
                    "parent_kind": parent.get("kind")
                },
                suggested_fix="Review type hierarchy"
            ))

        return violations

    def _check_variable_type_compatibility(self) -> List[Violation]:
        """
        Check that variable assignments are type-compatible.
        """
        violations = []

        # Check variables with type annotations that are assigned incompatible values
        query = """
        MATCH (v:Variable)
        OPTIONAL MATCH (v)-[:HAS_TYPE]->(declared:Type)
        OPTIONAL MATCH (v)-[:ASSIGNED_TYPE]->(assigned:Type)
        RETURN v, declared, collect(DISTINCT assigned.name) as inferred_types
        """
        results = self.db.execute_query(query)

        for record in results:
            var = dict(record["v"])
            declared_node = record.get("declared")
            declared_type = ""
            if declared_node:
                declared_type = dict(declared_node).get("name", "")
            elif var.get("type_annotation"):
                declared_type = var.get("type_annotation")

            inferred_types = [t for t in record.get("inferred_types", []) if t]

            # If we have both declared annotation and resolved type, check compatibility
            if declared_type:
                for resolved in set(inferred_types):
                    if resolved and resolved != declared_type:
                        if not self._types_compatible(resolved, declared_type):
                            violations.append(Violation(
                                violation_type=ViolationType.DATA_FLOW_INVALID,
                                severity="error",
                                entity_id=var["id"],
                                message=f"Variable {var['name']} declared as '{declared_type}' but assigned '{resolved}'",
                                details={
                                    "variable": var["name"],
                                    "declared_type": declared_type,
                                    "assigned_type": resolved,
                                    "scope": var.get("scope")
                                },
                                suggested_fix=f"Ensure assigned value matches type {declared_type}"
                            ))
            else:
                unique_inferred = sorted(set(inferred_types))
                if len(unique_inferred) > 1:
                    violations.append(Violation(
                        violation_type=ViolationType.DATA_FLOW_INVALID,
                        severity="warning",
                        entity_id=var["id"],
                        message=f"Variable {var['name']} assigned inconsistent inferred types: {', '.join(unique_inferred)}",
                        details={
                            "variable": var["name"],
                            "assigned_types": unique_inferred,
                            "scope": var.get("scope")
                        },
                        suggested_fix="Add an explicit annotation or ensure assignments use a consistent type"
                    ))

        return violations

    def _types_compatible(self, actual: str, expected: str) -> bool:
        """
        Check if actual type is compatible with expected type.
        This is a simplified check - full type compatibility requires the type graph.
        """
        if not actual or not expected:
            return True  # Unknown types are assumed compatible

        # Exact match
        if actual == expected:
            return True

        # Normalize type names
        actual = actual.strip()
        expected = expected.strip()

        # Any type is compatible with anything
        if expected == "Any" or actual == "Any":
            return True

        # None is compatible with Optional
        if actual == "None" and "Optional" in expected:
            return True

        # Basic numeric compatibility
        numeric_types = {"int", "float", "complex", "bool"}
        if actual in numeric_types and expected in numeric_types:
            # int is subtype of float, bool is subtype of int
            if actual == "bool" and expected in {"int", "float"}:
                return True
            if actual == "int" and expected == "float":
                return True

        # String compatibility
        if actual in {"str", "bytes"} and expected in {"str", "bytes", "Sequence"}:
            return True

        # List/Sequence compatibility
        if actual.startswith("List") and expected.startswith("Sequence"):
            return True

        # Dict/Mapping compatibility
        if actual.startswith("Dict") and expected.startswith("Mapping"):
            return True

        # Check generic type compatibility (simplified)
        if "[" in actual and "[" in expected:
            actual_base = actual.split("[")[0]
            expected_base = expected.split("[")[0]
            if actual_base == expected_base:
                return True  # Simplified - should check type parameters

        # Query the graph for IS_SUBTYPE_OF relationship
        query = """
        MATCH (a:Type {name: $actual})-[:IS_SUBTYPE_OF*0..5]->(e:Type {name: $expected})
        RETURN count(*) > 0 as compatible
        """
        try:
            results = self.db.execute_query(query, {"actual": actual, "expected": expected})
            if results and results[0].get("compatible"):
                return True
        except Exception:
            pass

        return False

    def validate_typing_with_pyright(self, files: List[str] = None) -> List[Violation]:
        """
        Run pyright type checker and convert diagnostics to violations.
        This provides deep T law validation beyond annotation presence.

        Args:
            files: Optional list of files to check. If None, checks all changed files.

        Returns:
            List of typing violations from pyright
        """
        violations = []

        logger.info("Running pyright type checking...")

        # Get files to check
        if files is None:
            # Get files from changed nodes
            query = """
            MATCH (n)
            WHERE n.changed = true AND n.location IS NOT NULL
            RETURN DISTINCT split(n.location, ':')[0] as file_path
            """
            results = self.db.execute_query(query)
            files = [r["file_path"] for r in results if r["file_path"] and os.path.exists(r["file_path"])]

        if not files:
            logger.info("No files to check with pyright")
            return violations

        # Run pyright
        try:
            result = subprocess.run(
                ['pyright', '--outputjson'] + files,
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse JSON output
            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse pyright output: {result.stdout[:500]}")
                return violations

            # Process diagnostics
            diagnostics = output.get('generalDiagnostics', [])

            for diag in diagnostics:
                severity = diag.get('severity', 'error')
                if severity not in ['error', 'warning']:
                    continue

                file_path = diag.get('file', '')
                range_info = diag.get('range', {})
                start = range_info.get('start', {})
                line_number = start.get('line', 0) + 1  # pyright uses 0-indexed lines
                column_number = start.get('character', 0)
                message = diag.get('message', '')
                rule = diag.get('rule', 'unknown')

                # Get code snippet
                code_snippet = None
                if file_path and line_number:
                    code_snippet = self._get_code_snippet(file_path, line_number)

                violations.append(Violation(
                    violation_type=ViolationType.DATA_FLOW_INVALID,
                    severity=severity,
                    entity_id=f"pyright:{file_path}:{line_number}:{column_number}",
                    message=f"[{rule}] {message}",
                    details={
                        "rule": rule,
                        "file": file_path,
                        "line": line_number,
                        "column": column_number,
                        "pyright_severity": severity
                    },
                    suggested_fix=f"Fix type error at {file_path}:{line_number}",
                    file_path=file_path,
                    line_number=line_number,
                    column_number=column_number,
                    code_snippet=code_snippet
                ))

            logger.info(f"Pyright found {len(violations)} type violations")

        except FileNotFoundError:
            logger.warning("pyright not found in PATH. Install with: npm install -g pyright")
        except subprocess.TimeoutExpired:
            logger.error("pyright timed out after 120 seconds")
        except Exception as e:
            logger.error(f"Error running pyright: {e}")

        return violations

    def validate_edge_types(self) -> List[Violation]:
        """
        Validate that edges connect valid node types according to the schema.
        This is part of the S (Structural) law.

        Returns:
            List of violations where edges connect wrong node types
        """
        violations = []

        logger.info("Validating edge type correctness...")

        # Define valid edge type mappings: edge_type -> (allowed_from_labels, allowed_to_labels)
        edge_schema = {
            "DECLARES": (["Module"], ["Class", "Function", "Variable"]),
            "DEFINES": (["Class"], ["Function"]),
            "HAS_PARAMETER": (["Function"], ["Parameter"]),
            "CALLS": (["CallSite"], ["Function"]),
            "HAS_CALLSITE": (["Function"], ["CallSite"]),
            "INHERITS": (["Class"], ["Class"]),
            "IMPORTS": (["Module"], ["Module"]),
            "RETURNS_TYPE": (["Function"], ["Type"]),
            "HAS_TYPE": (["Parameter", "Variable"], ["Type"]),
            "RESOLVES_TO": (["CallSite"], ["Function"]),
            "CONTAINS": (["Module", "Class", "Function"], ["Class", "Function", "Variable", "Parameter"]),
            "ASSIGNS_TO": (["Function"], ["Variable"]),
            "READS_FROM": (["Function"], ["Variable"]),
            "ASSIGNED_TYPE": (["Variable"], ["Type"]),
            "IS_SUBTYPE_OF": (["Type"], ["Type"]),
            "HAS_DECORATOR": (["Function", "Class"], ["Decorator"]),
            "DECORATES": (["Decorator"], ["Function", "Class"]),
            "REFERENCES": (["Function", "Class", "Decorator"], ["Variable", "Function", "Class", "Decorator", "Type"]),
            "UNRESOLVED_REFERENCE": (["Function", "Class", "Module"], ["Unresolved"]),
        }

        for edge_type, (valid_from, valid_to) in edge_schema.items():
            # Query for edges that violate the schema
            from_check = " OR ".join([f"'{l}' IN labels(a)" for l in valid_from])
            to_check = " OR ".join([f"'{l}' IN labels(b)" for l in valid_to])

            query = f"""
            MATCH (a)-[r:{edge_type}]->(b)
            WHERE NOT ({from_check}) OR NOT ({to_check})
            RETURN a, b, labels(a) as from_labels, labels(b) as to_labels
            LIMIT 100
            """

            try:
                results = self.db.execute_query(query)

                for record in results:
                    from_node = dict(record["a"])
                    to_node = dict(record["b"])
                    from_labels = record["from_labels"]
                    to_labels = record["to_labels"]

                    violations.append(Violation(
                        violation_type=ViolationType.STRUCTURAL_INVALID,
                        severity="error",
                        entity_id=from_node.get("id", "unknown"),
                        message=f"Invalid {edge_type} edge: {from_labels} -> {to_labels}",
                        details={
                            "edge_type": edge_type,
                            "from_node": from_node.get("id"),
                            "from_labels": from_labels,
                            "to_node": to_node.get("id"),
                            "to_labels": to_labels,
                            "expected_from": valid_from,
                            "expected_to": valid_to
                        },
                        suggested_fix=f"Edge {edge_type} should be from {valid_from} to {valid_to}"
                    ))
            except Exception as e:
                logger.warning(f"Error checking edge type {edge_type}: {e}")

        logger.info(f"Edge type validation: {len(violations)} violations")
        return violations

    def validate_structural_integrity(self) -> List[Violation]:
        """
        LAW 4: GRAPH STRUCTURAL INTEGRITY
        Edges must connect valid nodes, multiplicities preserved.

        Checks:
        - No dangling edges
        - Proper cardinalities (e.g., parameter belongs to exactly one function)
        - No circular inheritance
        - Parameter positions are sequential

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating structural integrity...")

        # First, check edge type correctness
        violations.extend(self.validate_edge_types())

        # Check parameter positions are sequential
        query = """
        MATCH (f:Function)-[r:HAS_PARAMETER]->(p:Parameter)
        WITH f, collect(r.position) as positions
        WHERE size(positions) > 0
        RETURN f, positions
        """
        functions = self.db.execute_query(query)

        for record in functions:
            func = dict(record["f"])
            positions = sorted(record["positions"])

            # Check for gaps in positions
            expected = list(range(len(positions)))
            if positions != expected:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="error",
                    entity_id=func["id"],
                    message=f"Function {func['name']} has non-sequential parameter positions",
                    details={
                        "function": func["qualified_name"],
                        "positions": positions,
                        "expected": expected
                    },
                    suggested_fix="Renumber parameters to be sequential starting from 0"
                ))

        # Check for circular call dependencies
        circular = self.query.find_circular_dependencies()
        if circular:
            for cycle in circular:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="error",
                    entity_id=cycle[0] if cycle else "unknown",
                    message=f"Circular call dependency detected",
                    details={
                        "cycle": cycle
                    },
                    suggested_fix="Break circular dependency by refactoring"
                ))

        # Check for circular inheritance
        inheritance_cycles = self.query.find_circular_inheritance()
        if inheritance_cycles:
            for cycle in inheritance_cycles:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="error",
                    entity_id=cycle[0] if cycle else "unknown",
                    message=f"Circular inheritance detected: {' -> '.join(cycle)}",
                    details={
                        "cycle": cycle
                    },
                    suggested_fix="Remove circular inheritance by refactoring class hierarchy"
                ))

        # Check for diamond inheritance patterns
        diamond_patterns = self.query.find_diamond_inheritance()
        if diamond_patterns:
            for pattern in diamond_patterns:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="warning",
                    entity_id=pattern["class"],
                    message=f"Diamond inheritance detected: {pattern['class']} inherits from {pattern['base']} via {pattern['path_count']} paths",
                    details={
                        "class": pattern["class"],
                        "base": pattern["base"],
                        "path_count": pattern["path_count"]
                    },
                    suggested_fix="Review class hierarchy and ensure MRO is understood"
                ))

        # Check that each parameter belongs to exactly one function
        query = """
        MATCH (p:Parameter)
        OPTIONAL MATCH (f:Function)-[:HAS_PARAMETER]->(p)
        WITH p, count(f) as func_count
        WHERE func_count <> 1
        RETURN p, func_count
        """
        bad_params = self.db.execute_query(query)

        for record in bad_params:
            param = dict(record["p"])
            func_count = record["func_count"]

            # Extract location info
            loc_info = self._extract_location(param)

            # Get code snippet
            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(
                    loc_info["file_path"],
                    loc_info["line_number"]
                )

            violations.append(Violation(
                violation_type=ViolationType.STRUCTURAL_INVALID,
                severity="error",
                entity_id=param["id"],
                message=f"Parameter {param['name']} belongs to {func_count} functions (expected 1)",
                details={
                    "parameter": param["name"],
                    "function_count": func_count
                },
                suggested_fix="Ensure parameter has exactly one parent function",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                old_value=func_count,
                new_value=1,
                code_snippet=code_snippet
            ))

        logger.info(f"Structural integrity: {len(violations)} violations")
        return violations

    def validate_change(self, entity_id: str, change_type: str, new_properties: Dict[str, Any] = None) -> List[Violation]:
        """
        Validate a proposed change against conservation laws.

        Args:
            entity_id: Entity to change
            change_type: Type of change (modify, delete, rename)
            new_properties: New properties for the entity

        Returns:
            List of violations the change would cause
        """
        violations = []

        logger.info(f"Validating {change_type} change to {entity_id}")

        # Get impact analysis
        impact = self.query.get_impact_analysis(entity_id, change_type)

        if change_type == "delete":
            # Deletion would break all references
            if impact["affected_callers"]:
                violations.append(Violation(
                    violation_type=ViolationType.REFERENCE_BROKEN,
                    severity="error",
                    entity_id=entity_id,
                    message=f"Deleting entity would break {len(impact['affected_callers'])} callers",
                    details={
                        "callers": impact["affected_callers"]
                    },
                    suggested_fix="Update or remove all call sites before deleting"
                ))

        elif change_type == "modify" and new_properties:
            # Check if signature change would break callers
            if "signature" in new_properties:
                # For now, flag any signature change as requiring review
                if impact["affected_callers"]:
                    violations.append(Violation(
                        violation_type=ViolationType.SIGNATURE_MISMATCH,
                        severity="warning",
                        entity_id=entity_id,
                        message=f"Signature change affects {len(impact['affected_callers'])} callers",
                        details={
                            "callers": impact["affected_callers"],
                            "new_signature": new_properties["signature"]
                        },
                        suggested_fix="Review and update all call sites to match new signature"
                    ))

        return violations

    def _build_report(self, violations: List[Violation]) -> Dict[str, Any]:
        """Create a rich report used by CLI/workflows."""
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]
        by_type: Dict[str, List[Violation]] = {}
        for violation in violations:
            key = violation.violation_type.value
            by_type.setdefault(key, []).append(violation)

        return {
            "total_violations": len(violations),
            "errors": len(errors),
            "warnings": len(warnings),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "violations": violations,
            "summary": {
                "signature_conservation": len(by_type.get(ViolationType.SIGNATURE_MISMATCH.value, [])),
                "reference_integrity": len(by_type.get(ViolationType.REFERENCE_BROKEN.value, [])),
                "data_flow_consistency": len(by_type.get(ViolationType.DATA_FLOW_INVALID.value, [])),
                "structural_integrity": len(by_type.get(ViolationType.STRUCTURAL_INVALID.value, []))
            }
        }

    def _serialize_violation(self, violation: Violation) -> Dict[str, Any]:
        """Convert Violation dataclass into JSON-friendly dict."""
        return {
            "violation_type": violation.violation_type.value,
            "severity": violation.severity,
            "entity_id": violation.entity_id,
            "message": violation.message,
            "details": violation.details,
            "suggested_fix": violation.suggested_fix,
            "file_path": violation.file_path,
            "line_number": violation.line_number,
            "column_number": violation.column_number,
            "old_value": violation.old_value,
            "new_value": violation.new_value,
            "code_snippet": violation.code_snippet
        }

    def _serialize_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Make a report safe for JSON responses."""
        return {
            **{k: v for k, v in report.items() if k != "violations"},
            "violations": [self._serialize_violation(v) for v in report["violations"]]
        }

    def run_structural_checks(self) -> List[Violation]:
        """Run all Structural (S law) checks."""
        violations = []
        violations.extend(self.validate_signature_conservation())
        violations.extend(self.validate_structural_integrity())
        return violations

    def run_reference_checks(self) -> List[Violation]:
        """Run Referential (R law) checks."""
        return self.validate_reference_integrity()

    def run_typing_checks(self, include_pyright: bool = False) -> List[Violation]:
        """Run Typing/Data Flow (T law) checks."""
        violations = []
        violations.extend(self.validate_data_flow_consistency())
        if include_pyright:
            violations.extend(self.validate_typing_with_pyright())
        return violations

    def _collect_law_violations(self, include_pyright: bool = False) -> Dict[str, List[Violation]]:
        """Gather violations grouped by conservation law."""
        return {
            "structural": self.run_structural_checks(),
            "reference": self.run_reference_checks(),
            "typing": self.run_typing_checks(include_pyright=include_pyright)
        }

    def _law_report(self, law_name: str, violations: List[Violation]) -> Dict[str, Any]:
        """Build a report dictionary for a specific law."""
        report = self._build_report(violations)
        report["law"] = law_name
        return report

    def get_structural_report(self) -> Dict[str, Any]:
        """Return serialized structural validation results."""
        report = self._law_report("structural", self.run_structural_checks())
        return self._serialize_report(report)

    def get_reference_report(self) -> Dict[str, Any]:
        """Return serialized referential validation results."""
        report = self._law_report("reference", self.run_reference_checks())
        return self._serialize_report(report)

    def get_typing_report(self, include_pyright: bool = False) -> Dict[str, Any]:
        """Return serialized typing validation results."""
        report = self._law_report("typing", self.run_typing_checks(include_pyright=include_pyright))
        return self._serialize_report(report)

    def validate(self, incremental: bool = False, include_pyright: bool = False) -> Dict[str, Any]:
        """
        Run validation and return a JSON-friendly report. Used by FastAPI layer.
        """
        if incremental:
            violations = self.validate_incremental(include_pyright=include_pyright)
            report = self._build_report(violations)
            report["laws"] = {}
            serialized = self._serialize_report(report)
            serialized["laws"] = {}
            self._last_report = serialized
            return serialized
        else:
            law_map = self._collect_law_violations(include_pyright=include_pyright)
            violations: List[Violation] = []
            for law_violations in law_map.values():
                violations.extend(law_violations)

            report = self._build_report(violations)
            law_reports = {name: self._law_report(name, law_violations) for name, law_violations in law_map.items()}
            report["laws"] = law_reports

            serialized = self._serialize_report(report)
            serialized["laws"] = {
                name: self._serialize_report(law_report)
                for name, law_report in law_reports.items()
            }
            self._last_report = serialized
            return serialized

    def get_last_report(self) -> Dict[str, Any]:
        """Return last serialized report or an empty default."""
        if self._last_report is None:
            return {
                "total_violations": 0,
                "errors": 0,
                "warnings": 0,
                "by_type": {},
                "violations": [],
                "summary": {},
                "laws": {}
            }
        return self._last_report

    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive validation report for local tooling.

        Returns:
            Dictionary with validation results and statistics
        """
        law_map = self._collect_law_violations()
        violations: List[Violation] = []
        for law_violations in law_map.values():
            violations.extend(law_violations)

        report = self._build_report(violations)
        law_reports = {name: self._law_report(name, law_violations) for name, law_violations in law_map.items()}
        report["laws"] = law_reports
        serialized = self._serialize_report(report)
        serialized["laws"] = {
            name: self._serialize_report(law_report)
            for name, law_report in law_reports.items()
        }
        self._last_report = serialized
        return report

    # ========== Incremental Validation Methods ==========

    def validate_incremental(self, include_pyright: bool = False) -> List[Violation]:
        """
        Run conservation law validation only on changed nodes.
        This implements the Local-to-Global Soundness Theorem from the theory.

        Assumes changed flags have been set and propagated via db.propagate_changed_flag().

        Args:
            include_pyright: Whether to run pyright for deep type checking

        Returns:
            List of violations found in changed nodes
        """
        violations = []

        logger.info("Running incremental conservation law validation on changed nodes...")

        # S Law - Structural Validity
        violations.extend(self.validate_structural_integrity_incremental())

        # R Law - Referential Coherence
        violations.extend(self.validate_reference_integrity_incremental())

        # T Law - Semantic Typing Correctness
        violations.extend(self.validate_signature_conservation_incremental())
        violations.extend(self.validate_data_flow_consistency_incremental())

        # Optional deep type checking with pyright on changed files
        if include_pyright:
            violations.extend(self.validate_typing_with_pyright())  # Uses changed files by default

        logger.info(f"Incremental validation complete: {len(violations)} violations found")

        return violations

    def validate_signature_conservation_incremental(self) -> List[Violation]:
        """
        Validate signature conservation only for changed functions and their callers.

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating signature conservation (incremental)...")

        # Get only changed functions
        query = "MATCH (f:Function) WHERE f.changed = true RETURN f"
        functions = self.db.execute_query(query)

        for func_record in functions:
            func = dict(func_record["f"])
            func_id = func["id"]

            # Skip functions with signature-transforming decorators
            if self._has_transforming_decorator(func):
                continue

            # Get function parameters
            sig_info = self.query.get_function_signature(func_id)
            if not sig_info:
                continue

            params = sig_info["parameters"]

            # Adjust for self/cls parameters
            params_to_check = params
            if func.get("is_classmethod") or func.get("is_staticmethod") or func.get("is_property"):
                if params and params[0].get("param", {}).get("name") in ["self", "cls"]:
                    params_to_check = params[1:]
            elif params and params[0].get("param", {}).get("name") == "self":
                params_to_check = params[1:]

            total_params = len(params_to_check)
            required_params = sum(1 for p in params_to_check if not p.get("param", {}).get("default_value"))

            # Check all callers (including those marked as changed)
            callers = self.query.find_callers(func_id)

            for caller_info in callers:
                caller = caller_info["caller"]
                arg_count = caller_info.get("arg_count")
                location = caller_info.get("location", "unknown")

                if arg_count is not None:
                    if arg_count < required_params or arg_count > total_params:
                        loc_info = self._parse_location_string(location)
                        code_snippet = None
                        if loc_info["file_path"] and loc_info["line_number"]:
                            code_snippet = self._get_code_snippet(loc_info["file_path"], loc_info["line_number"])

                        if required_params == total_params:
                            expected_msg = f"{required_params} argument{'s' if required_params != 1 else ''}"
                        else:
                            expected_msg = f"{required_params}-{total_params} arguments"

                        violations.append(Violation(
                            violation_type=ViolationType.SIGNATURE_MISMATCH,
                            severity="error",
                            entity_id=func_id,
                            message=f"Function {func['name']} expects {expected_msg} but is called with {arg_count}",
                            details={
                                "function": func["qualified_name"],
                                "required_params": required_params,
                                "total_params": total_params,
                                "actual_args": arg_count,
                                "caller": caller["qualified_name"],
                                "location": location
                            },
                            suggested_fix=f"Update call at {location} to provide {expected_msg}",
                            file_path=loc_info["file_path"],
                            line_number=loc_info["line_number"],
                            column_number=loc_info["column_number"],
                            old_value=arg_count,
                            new_value=required_params if arg_count < required_params else total_params,
                            code_snippet=code_snippet
                        ))

        logger.info(f"Signature conservation (incremental): {len(violations)} violations")
        return violations

    def validate_reference_integrity_incremental(self) -> List[Violation]:
        """
        Validate reference integrity only for changed nodes.

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating reference integrity (incremental)...")

        # Check unresolved call sites in changed nodes
        query = """
        MATCH (cs:CallSite)
        WHERE cs.changed = true AND cs.resolution_status = 'unresolved'
        RETURN cs
        """
        unresolved = self.db.execute_query(query)

        for record in unresolved:
            cs = dict(record["cs"])
            loc_info = self._parse_location_string(cs.get("location", ""))

            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(loc_info["file_path"], loc_info["line_number"])

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=cs["id"],
                message=f"Unresolved call to: {cs.get('unresolved_callee', 'unknown')}",
                details={
                    "callsite": cs.get("name"),
                    "callee_name": cs.get("unresolved_callee"),
                    "location": cs.get("location")
                },
                suggested_fix="Ensure the called function exists and is in scope",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"],
                code_snippet=code_snippet
            ))

        # Check RESOLVES_TO relationships for changed CallSites
        query = """
        MATCH (cs:CallSite)
        WHERE cs.changed = true
        OPTIONAL MATCH (cs)-[:RESOLVES_TO]->(f:Function)
        WITH cs, count(f) as target_count
        WHERE target_count <> 1 AND cs.resolution_status <> 'unresolved'
        RETURN cs, target_count
        """
        bad_resolutions = self.db.execute_query(query)

        for record in bad_resolutions:
            cs = dict(record["cs"])
            target_count = record["target_count"]

            loc_info = self._parse_location_string(cs.get("location", ""))

            violations.append(Violation(
                violation_type=ViolationType.REFERENCE_BROKEN,
                severity="error",
                entity_id=cs["id"],
                message=f"CallSite resolves to {target_count} targets (expected 1)",
                details={
                    "callsite": cs.get("name"),
                    "target_count": target_count,
                    "location": cs.get("location")
                },
                suggested_fix="Ensure call resolves to exactly one function",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"]
            ))

        logger.info(f"Reference integrity (incremental): {len(violations)} violations")
        return violations

    def validate_data_flow_consistency_incremental(self) -> List[Violation]:
        """
        Validate data flow consistency only for changed nodes.
        Implements the T law for the semantic light cone of changes.

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating data flow consistency (incremental)...")

        # 1. Check changed parameters missing type annotations
        query = """
        MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
        WHERE (f.changed = true OR p.changed = true)
          AND p.type_annotation IS NULL
          AND NOT p.name IN ['self', 'cls']
        RETURN f, p
        """
        untyped_params = self.db.execute_query(query)

        for record in untyped_params:
            func = dict(record["f"])
            param = dict(record["p"])

            loc_info = self._parse_location_string(func.get("location", ""))

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=param["id"],
                message=f"Parameter {param['name']} in {func['name']} missing type annotation",
                details={
                    "function": func["qualified_name"],
                    "parameter": param["name"],
                    "position": param.get("position")
                },
                suggested_fix=f"Add type annotation to parameter {param['name']}",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"]
            ))

        # 2. Check changed functions missing return type annotations
        query = """
        MATCH (f:Function)
        WHERE f.changed = true
          AND f.return_type IS NULL
          AND NOT f.name STARTS WITH '_'
          AND NOT f.name = '__init__'
        RETURN f
        """
        untyped_functions = self.db.execute_query(query)

        for record in untyped_functions:
            func = dict(record["f"])
            loc_info = self._parse_location_string(func.get("location", ""))

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="warning",
                entity_id=func["id"],
                message=f"Function {func['name']} missing return type annotation",
                details={"function": func["qualified_name"]},
                suggested_fix="Add return type annotation",
                file_path=loc_info["file_path"],
                line_number=loc_info["line_number"],
                column_number=loc_info["column_number"]
            ))

        # 3. Check type compatibility at changed call sites
        query = """
        MATCH (cs:CallSite)-[:CALLS]->(f:Function)-[:HAS_PARAMETER]->(p:Parameter)
        WHERE (cs.changed = true OR f.changed = true)
          AND p.type_annotation IS NOT NULL
        OPTIONAL MATCH (p)-[:HAS_TYPE]->(pt:Type)
        WITH cs, f, p, pt
        ORDER BY p.position
        RETURN cs, f, collect({param: p, type: pt}) as params
        """
        results = self.db.execute_query(query)

        for record in results:
            cs = dict(record["cs"])
            func = dict(record["f"])
            params = record["params"]

            arg_types = cs.get("arg_types", [])
            if not arg_types:
                continue

            for i, param_info in enumerate(params):
                if i >= len(arg_types):
                    break

                param = param_info.get("param", {})
                param_type = param_info.get("type", {})

                if not param_type:
                    continue

                arg_type = arg_types[i]
                if not arg_type:
                    continue
                expected_type = param_type.get("name", param.get("type_annotation", ""))

                if arg_type and expected_type:
                    if not self._types_compatible(arg_type, expected_type):
                        loc_info = self._parse_location_string(cs.get("location", ""))

                        violations.append(Violation(
                            violation_type=ViolationType.DATA_FLOW_INVALID,
                            severity="error",
                            entity_id=cs["id"],
                            message=f"Type mismatch: argument {i+1} is '{arg_type}' but parameter '{param.get('name')}' expects '{expected_type}'",
                            details={
                                "callsite": cs.get("name"),
                                "function": func.get("qualified_name"),
                                "parameter": param.get("name"),
                                "position": i,
                                "arg_type": arg_type,
                                "expected_type": expected_type
                            },
                            suggested_fix=f"Convert argument to {expected_type} or update parameter type",
                            file_path=loc_info["file_path"],
                            line_number=loc_info["line_number"],
                            column_number=loc_info["column_number"]
                        ))

        # 4. Check subtype cycles involving changed types
        query = """
        MATCH (t:Type)
        WHERE t.changed = true
        MATCH path = (t)-[:IS_SUBTYPE_OF*1..]->(t)
        RETURN t, [n IN nodes(path) | n.name] as cycle
        LIMIT 10
        """
        cycles = self.db.execute_query(query)

        for record in cycles:
            type_node = dict(record["t"])
            cycle = record["cycle"]

            violations.append(Violation(
                violation_type=ViolationType.DATA_FLOW_INVALID,
                severity="error",
                entity_id=type_node.get("id", "unknown"),
                message=f"Circular subtype relationship: {' -> '.join(cycle)}",
                details={"cycle": cycle},
                suggested_fix="Remove circular subtype relationship"
            ))

        # 5. Check variable type compatibility for changed assignments
        query = """
        MATCH (f:Function)-[:ASSIGNS_TO]->(v:Variable)
        WHERE (f.changed = true OR v.changed = true)
          AND v.type_annotation IS NOT NULL
        OPTIONAL MATCH (v)-[:HAS_TYPE]->(vt:Type)
        RETURN f, v, vt
        """
        results = self.db.execute_query(query)

        for record in results:
            func = dict(record["f"])
            var = dict(record["v"])
            var_type = dict(record["vt"]) if record["vt"] else None

            declared = var.get("type_annotation")
            resolved = var_type.get("name") if var_type else None

            if declared and resolved and declared != resolved:
                if not self._types_compatible(resolved, declared):
                    violations.append(Violation(
                        violation_type=ViolationType.DATA_FLOW_INVALID,
                        severity="error",
                        entity_id=var["id"],
                        message=f"Variable {var['name']} declared as '{declared}' but assigned '{resolved}'",
                        details={
                            "variable": var["name"],
                            "declared_type": declared,
                            "assigned_type": resolved,
                            "function": func.get("qualified_name")
                        },
                        suggested_fix=f"Ensure assigned value matches type {declared}"
                    ))

        logger.info(f"Data flow consistency (incremental): {len(violations)} violations")
        return violations

    def validate_structural_integrity_incremental(self) -> List[Violation]:
        """
        Validate structural integrity only for changed nodes.

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating structural integrity (incremental)...")

        # Check parameter positions for changed functions
        query = """
        MATCH (f:Function)-[r:HAS_PARAMETER]->(p:Parameter)
        WHERE f.changed = true
        WITH f, collect(r.position) as positions
        WHERE size(positions) > 0
        RETURN f, positions
        """
        functions = self.db.execute_query(query)

        for record in functions:
            func = dict(record["f"])
            positions = sorted(record["positions"])

            expected = list(range(len(positions)))
            if positions != expected:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="error",
                    entity_id=func["id"],
                    message=f"Function {func['name']} has non-sequential parameter positions",
                    details={
                        "function": func["qualified_name"],
                        "positions": positions,
                        "expected": expected
                    },
                    suggested_fix="Renumber parameters to be sequential starting from 0"
                ))

        # Check for inheritance cycles involving changed classes
        query = """
        MATCH (c:Class)
        WHERE c.changed = true
        MATCH path = (c)-[:INHERITS*1..]->(c)
        RETURN [node in nodes(path) | node.qualified_name] as cycle
        LIMIT 10
        """
        cycles = self.db.execute_query(query)

        for record in cycles:
            cycle = record["cycle"]
            violations.append(Violation(
                violation_type=ViolationType.STRUCTURAL_INVALID,
                severity="error",
                entity_id=cycle[0] if cycle else "unknown",
                message=f"Circular inheritance detected: {' -> '.join(cycle)}",
                details={"cycle": cycle},
                suggested_fix="Remove circular inheritance by refactoring class hierarchy"
            ))

        # Check parameter ownership for changed parameters
        query = """
        MATCH (p:Parameter)
        WHERE p.changed = true
        OPTIONAL MATCH (f:Function)-[:HAS_PARAMETER]->(p)
        WITH p, count(f) as func_count
        WHERE func_count <> 1
        RETURN p, func_count
        """
        bad_params = self.db.execute_query(query)

        for record in bad_params:
            param = dict(record["p"])
            func_count = record["func_count"]

            violations.append(Violation(
                violation_type=ViolationType.STRUCTURAL_INVALID,
                severity="error",
                entity_id=param["id"],
                message=f"Parameter {param['name']} belongs to {func_count} functions (expected 1)",
                details={
                    "parameter": param["name"],
                    "function_count": func_count
                },
                suggested_fix="Ensure parameter has exactly one parent function"
            ))

        logger.info(f"Structural integrity (incremental): {len(violations)} violations")
        return violations

    def get_incremental_validation_report(self) -> Dict[str, Any]:
        """
        Get validation report for only changed nodes.

        Returns:
            Dictionary with validation results and statistics
        """
        violations = self.validate_incremental()

        # Group by severity
        errors = [v for v in violations if v.severity == "error"]
        warnings = [v for v in violations if v.severity == "warning"]

        # Group by type
        by_type = {}
        for v in violations:
            type_name = v.violation_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(v)

        # Get changed node count
        changed_nodes = self.db.get_changed_node_ids()

        return {
            "total_violations": len(violations),
            "errors": len(errors),
            "warnings": len(warnings),
            "changed_nodes": len(changed_nodes),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "violations": violations,
            "summary": {
                "signature_conservation": len(by_type.get(ViolationType.SIGNATURE_MISMATCH.value, [])),
                "reference_integrity": len(by_type.get(ViolationType.REFERENCE_BROKEN.value, [])),
                "data_flow_consistency": len(by_type.get(ViolationType.DATA_FLOW_INVALID.value, [])),
                "structural_integrity": len(by_type.get(ViolationType.STRUCTURAL_INVALID.value, []))
            }
        }
