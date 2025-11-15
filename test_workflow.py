#!/usr/bin/env python3
"""Test script for workflow orchestration."""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from codegraph.db import CodeGraphDB
from codegraph.workflow import WorkflowOrchestrator

# Connect to Neo4j
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

async def test_workflow():
    """Test the workflow orchestrator."""
    print("="*80)
    print("Testing Workflow Orchestrator")
    print("="*80)

    # Initialize
    db = CodeGraphDB(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
    orchestrator = WorkflowOrchestrator(db)

    # Use the same path format as the backend uses (local path)
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend", "examples", "connected_example.py"))

    print(f"\n1. Testing validate_after_edit workflow...")
    print(f"   File: {file_path}")

    # Run workflow
    result = orchestrator.validate_after_edit(
        file_paths=[file_path],
        description="Added optional parameter to calculate_total",
        create_snapshot=True,
        compare_with_previous=True
    )

    print(f"\n   Workflow ID: {result.workflow_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Steps completed: {', '.join(result.steps_completed)}")
    print(f"   Entities indexed: {result.entities_indexed}")
    print(f"   Relationships indexed: {result.relationships_indexed}")

    if result.snapshot_id:
        print(f"   Snapshot created: {result.snapshot_id}")

    if result.changes_detected:
        print(f"\n   Changes detected:")
        for key, value in result.changes_detected.items():
            print(f"      {key}: {value}")

    print(f"\n   Validation results:")
    print(f"      Total violations: {result.total_violations}")
    print(f"      Errors: {result.errors}")
    print(f"      Warnings: {result.warnings}")
    print(f"      Is valid: {result.is_valid}")
    print(f"      Needs fixes: {result.needs_fixes}")
    # Remove emojis from message
    message = result.message.replace("✅", "[OK]").replace("❌", "[ERROR]")
    print(f"      Message: {message}")

    if result.violations:
        print(f"\n   Violations in connected_example.py:")
        connected_violations = [v for v in result.violations if v.get('file_path') and 'connected_example.py' in v.get('file_path')]
        if connected_violations:
            for v in connected_violations[:10]:  # Show first 10
                print(f"      [{v['severity'].upper()}] {v['message']}")
                if v.get('file_path'):
                    print(f"         Location: {v['file_path']}:{v.get('line_number', '?')}:{v.get('column_number', '?')}")
        else:
            print(f"      None! The workflow successfully validated the changes!")

    print("\n" + "="*80)
    print("Test complete!")
    print("="*80)

    # Close connection
    db.close()

if __name__ == "__main__":
    asyncio.run(test_workflow())
