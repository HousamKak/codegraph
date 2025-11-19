"""
Workflow Orchestrator for CodeGraph

This module provides high-level workflow operations that combine multiple
low-level tools into cohesive processes for LLM code editing.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from .db import CodeGraphDB
from .parser import PythonParser
from .builder import GraphBuilder
from .validators import ConservationValidator
from .snapshot import SnapshotManager

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    INDEXING = "indexing"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""
    workflow_id: str
    status: WorkflowStatus
    timestamp: str
    steps_completed: List[str]

    # Indexing results
    entities_indexed: int
    relationships_indexed: int

    # Snapshot results
    snapshot_id: Optional[str] = None
    previous_snapshot_id: Optional[str] = None
    changes_detected: Optional[Dict[str, int]] = None

    # Validation results
    total_violations: int = 0
    errors: int = 0
    warnings: int = 0
    violations: List[Dict[str, Any]] = None

    # Overall assessment
    is_valid: bool = False
    needs_fixes: bool = False
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['status'] = self.status.value
        return result


class WorkflowOrchestrator:
    """
    Orchestrates high-level workflows combining multiple operations.

    This class provides composite operations that combine indexing, snapshot
    comparison, and validation into single workflow steps.
    """

    def __init__(self, db: CodeGraphDB):
        """Initialize the orchestrator."""
        self.db = db
        self.parser = PythonParser()
        self.builder = GraphBuilder(db)
        self.validator = ConservationValidator(db)
        self.snapshot_manager = SnapshotManager(db)

        logger.info("WorkflowOrchestrator initialized")

    def validate_after_edit(
        self,
        file_paths: List[str],
        description: str = "",
        create_snapshot: bool = True,
        compare_with_previous: bool = True
    ) -> WorkflowResult:
        """
        Complete workflow after LLM edits files.

        This combines:
        1. Re-index modified files
        2. Create new snapshot (optional)
        3. Compare with previous snapshot (optional)
        4. Validate against conservation laws
        5. Return comprehensive results

        Args:
            file_paths: List of file paths that were edited
            description: Description of the changes made
            create_snapshot: Whether to create a snapshot
            compare_with_previous: Whether to compare with previous snapshot

        Returns:
            WorkflowResult with complete analysis
        """
        workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        steps_completed = []

        logger.info(f"Starting workflow {workflow_id}: validate_after_edit")
        logger.info(f"Files to re-index: {file_paths}")

        try:
            # Get previous snapshot if comparing
            previous_snapshot_id = None
            if compare_with_previous:
                snapshots = self.snapshot_manager.list_snapshots()
                if snapshots:
                    # Get the most recent snapshot
                    previous_snapshot_id = snapshots[-1].snapshot_id
                    logger.info(f"Will compare with previous snapshot: {previous_snapshot_id}")

            # Step 1: Re-index all modified files
            logger.info("Step 1: Re-indexing modified files...")
            total_entities = 0
            total_relationships = 0

            for file_path in file_paths:
                # Delete old nodes from this file
                self.db.delete_nodes_from_file(file_path)

                # Parse and build graph
                entities, relationships = self.parser.parse_file(file_path)
                self.builder.build_graph(entities, relationships)

                total_entities += len(entities)
                total_relationships += len(relationships)

                logger.info(f"Re-indexed {file_path}: {len(entities)} entities, {len(relationships)} relationships")

            steps_completed.append("re-indexing")

            # Step 2: Create new snapshot
            new_snapshot_id = None
            changes_detected = None

            if create_snapshot:
                logger.info("Step 2: Creating new snapshot...")
                snapshot_desc = description or f"After editing {len(file_paths)} file(s)"
                new_snapshot_id = self.snapshot_manager.create_snapshot(snapshot_desc)
                logger.info(f"Created snapshot: {new_snapshot_id}")
                steps_completed.append("snapshot_created")

                # Step 3: Compare with previous snapshot
                if compare_with_previous and previous_snapshot_id:
                    logger.info("Step 3: Comparing snapshots...")
                    diff = self.snapshot_manager.compare_snapshots(
                        previous_snapshot_id,
                        new_snapshot_id
                    )

                    changes_detected = {
                        "nodes_added": len(diff.nodes.added),
                        "nodes_removed": len(diff.nodes.removed),
                        "nodes_modified": len(diff.nodes.modified),
                        "edges_added": len(diff.edges.added),
                        "edges_removed": len(diff.edges.removed),
                        "edges_modified": len(diff.edges.modified)
                    }

                    logger.info(f"Changes detected: {changes_detected}")
                    steps_completed.append("snapshot_comparison")

            # Step 4: Validate
            logger.info("Step 4: Validating codebase...")
            validation_report = self.validator.get_validation_report()

            # Format violations
            formatted_violations = []
            for v in validation_report['violations']:
                formatted_violations.append({
                    "type": v.violation_type.value,
                    "severity": v.severity,
                    "entity_id": v.entity_id,
                    "message": v.message,
                    "file_path": v.file_path,
                    "line_number": v.line_number,
                    "column_number": v.column_number,
                    "code_snippet": v.code_snippet,
                    "suggested_fix": v.suggested_fix,
                    "details": v.details
                })

            steps_completed.append("validation")

            # Determine overall status
            is_valid = validation_report['errors'] == 0
            needs_fixes = validation_report['errors'] > 0

            if is_valid:
                message = f"✅ Validation passed! {validation_report['warnings']} warning(s) found."
            else:
                message = f"❌ Validation failed: {validation_report['errors']} error(s), {validation_report['warnings']} warning(s) found."

            logger.info(message)

            # Build result
            result = WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.COMPLETED,
                timestamp=datetime.now().isoformat(),
                steps_completed=steps_completed,
                entities_indexed=total_entities,
                relationships_indexed=total_relationships,
                snapshot_id=new_snapshot_id,
                previous_snapshot_id=previous_snapshot_id,
                changes_detected=changes_detected,
                total_violations=validation_report['total_violations'],
                errors=validation_report['errors'],
                warnings=validation_report['warnings'],
                violations=formatted_violations,
                is_valid=is_valid,
                needs_fixes=needs_fixes,
                message=message
            )

            logger.info(f"Workflow {workflow_id} completed successfully")
            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            return WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                timestamp=datetime.now().isoformat(),
                steps_completed=steps_completed,
                entities_indexed=0,
                relationships_indexed=0,
                total_violations=0,
                errors=0,
                warnings=0,
                violations=[],
                is_valid=False,
                needs_fixes=False,
                message=f"Workflow failed: {str(e)}"
            )

    def prepare_for_editing(
        self,
        file_paths: List[str],
        description: str = ""
    ) -> WorkflowResult:
        """
        Prepare before LLM starts editing.

        This creates a baseline snapshot to compare against later.

        Args:
            file_paths: List of files that will be edited
            description: Description of planned changes

        Returns:
            WorkflowResult with baseline snapshot info
        """
        workflow_id = f"prepare_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting workflow {workflow_id}: prepare_for_editing")
        logger.info(f"Files to be edited: {file_paths}")

        try:
            # Create baseline snapshot
            snapshot_desc = description or f"Before editing {len(file_paths)} file(s)"
            snapshot_id = self.snapshot_manager.create_snapshot(snapshot_desc)

            logger.info(f"Created baseline snapshot: {snapshot_id}")

            # Get current stats
            stats = self.db.get_statistics()
            relationship_total = stats.get("Relationships", 0)
            node_total = sum(
                count for key, count in stats.items()
                if key != "Relationships"
            )

            result = WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.COMPLETED,
                timestamp=datetime.now().isoformat(),
                steps_completed=["baseline_snapshot"],
                entities_indexed=node_total,
                relationships_indexed=relationship_total,
                snapshot_id=snapshot_id,
                total_violations=0,
                errors=0,
                warnings=0,
                violations=[],
                is_valid=True,
                needs_fixes=False,
                message=f"✅ Baseline snapshot created: {snapshot_id}"
            )

            logger.info(f"Workflow {workflow_id} completed")
            return result

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            return WorkflowResult(
                workflow_id=workflow_id,
                status=WorkflowStatus.FAILED,
                timestamp=datetime.now().isoformat(),
                steps_completed=[],
                entities_indexed=0,
                relationships_indexed=0,
                total_violations=0,
                errors=0,
                warnings=0,
                violations=[],
                is_valid=False,
                needs_fixes=False,
                message=f"Workflow failed: {str(e)}"
            )

    def iterative_fix_loop(
        self,
        file_paths: List[str],
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run iterative validation and fixing loop.

        This is a framework for automated fixing (though actual fixes are done by LLM).
        It validates, reports issues, and tracks progress over iterations.

        Args:
            file_paths: Files to validate
            max_iterations: Maximum number of iterations

        Returns:
            Summary of all iterations
        """
        logger.info(f"Starting iterative fix loop for {file_paths}")

        iterations = []

        for i in range(max_iterations):
            logger.info(f"Iteration {i + 1}/{max_iterations}")

            # Validate current state
            result = self.validate_after_edit(
                file_paths=file_paths,
                description=f"Iteration {i + 1}",
                create_snapshot=True,
                compare_with_previous=i > 0
            )

            iterations.append({
                "iteration": i + 1,
                "errors": result.errors,
                "warnings": result.warnings,
                "is_valid": result.is_valid,
                "violations": result.violations
            })

            # If valid, we're done
            if result.is_valid:
                logger.info(f"✅ Code is valid after {i + 1} iteration(s)")
                break

            logger.info(f"⚠️ Found {result.errors} error(s), continuing...")

        final_iteration = iterations[-1]

        return {
            "total_iterations": len(iterations),
            "final_status": "valid" if final_iteration["is_valid"] else "invalid",
            "final_errors": final_iteration["errors"],
            "final_warnings": final_iteration["warnings"],
            "iterations": iterations,
            "converged": final_iteration["is_valid"]
        }
