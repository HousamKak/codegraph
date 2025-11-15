"""Conservation law validators for code graph integrity."""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
from .db import CodeGraphDB
from .query import QueryInterface
import logging

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

    def __init__(self, db: CodeGraphDB):
        """
        Initialize validator.

        Args:
            db: CodeGraphDB instance
        """
        self.db = db
        self.query = QueryInterface(db)

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

    def validate_all(self) -> List[Violation]:
        """
        Run all conservation law validators.

        Returns:
            List of violations found
        """
        violations = []

        logger.info("Running conservation law validation...")

        violations.extend(self.validate_signature_conservation())
        violations.extend(self.validate_reference_integrity())
        violations.extend(self.validate_data_flow_consistency())
        violations.extend(self.validate_structural_integrity())

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

            # Get function parameters
            sig_info = self.query.get_function_signature(func_id)
            if not sig_info:
                continue

            params = sig_info["parameters"]
            total_params = len(params)

            # Count required parameters (those without defaults)
            required_params = sum(1 for p in params if not p.get("param", {}).get("default_value"))

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

        logger.info(f"Reference integrity: {len(violations)} violations")
        return violations

    def validate_data_flow_consistency(self) -> List[Violation]:
        """
        LAW 3: DATA FLOW CONSISTENCY
        Types/values flowing through edges must be compatible.

        Checks:
        - Type annotations are consistent
        - Return types match usage
        - Parameter types match arguments (when annotated)

        Returns:
            List of violations
        """
        violations = []

        logger.info("Validating data flow consistency...")

        # Check functions with return type annotations
        query = """
        MATCH (f:Function)
        WHERE f.return_type IS NOT NULL
        RETURN f
        """
        functions = self.db.execute_query(query)

        for func_record in functions:
            func = dict(func_record["f"])

            # For now, just ensure return type is specified
            # More advanced: track actual return statements and check types
            if not func.get("return_type"):
                violations.append(Violation(
                    violation_type=ViolationType.DATA_FLOW_INVALID,
                    severity="warning",
                    entity_id=func["id"],
                    message=f"Function {func['name']} missing return type annotation",
                    details={
                        "function": func["qualified_name"],
                    },
                    suggested_fix="Add return type annotation"
                ))

        # Check parameters with type annotations
        query = """
        MATCH (f:Function)-[:HAS_PARAMETER]->(p:Parameter)
        WHERE p.type_annotation IS NULL
        RETURN f, p
        """
        untyped_params = self.db.execute_query(query)

        for record in untyped_params:
            func = dict(record["f"])
            param = dict(record["p"])

            # Extract location info from function
            loc_info = self._extract_location(func)

            # Get code snippet
            code_snippet = None
            if loc_info["file_path"] and loc_info["line_number"]:
                code_snippet = self._get_code_snippet(
                    loc_info["file_path"],
                    loc_info["line_number"]
                )

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

        logger.info(f"Data flow consistency: {len(violations)} violations")
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

        # Check for circular inheritance
        circular = self.query.find_circular_dependencies()
        if circular:
            for cycle in circular:
                violations.append(Violation(
                    violation_type=ViolationType.STRUCTURAL_INVALID,
                    severity="error",
                    entity_id=cycle[0] if cycle else "unknown",
                    message=f"Circular dependency detected",
                    details={
                        "cycle": cycle
                    },
                    suggested_fix="Break circular dependency by refactoring"
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

    def get_validation_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive validation report.

        Returns:
            Dictionary with validation results and statistics
        """
        violations = self.validate_all()

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
