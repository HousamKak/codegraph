"""
Example demonstrating the complete LLM self-correcting code editor workflow.

This example shows:
1. Preparing an editing session
2. Making code edits
3. Automatic validation
4. Getting fix suggestions
5. Applying fixes
6. Committing changes

Run this with the backend running on localhost:8000
"""

import requests
import json
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"


def pretty_print(title: str, data: Dict[str, Any]):
    """Print formatted JSON data."""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}")
    print(json.dumps(data, indent=2))
    print()


def test_validation_workflow():
    """Test the complete validation workflow."""

    print("\n" + "="*80)
    print("CODEGRAPH VALIDATION WORKFLOW DEMONSTRATION")
    print("="*80)

    # Step 1: Prepare editing session
    print("\nStep 1: Preparing editing session...")
    response = requests.post(
        f"{BASE_URL}/session/prepare",
        json={"description": "Add new data processing function"}
    )
    response.raise_for_status()
    session_data = response.json()
    session_id = session_data["session_id"]
    pretty_print("Session Prepared", session_data)

    # Step 2: Add a code edit that will cause violations
    print("\nStep 2: Adding code edit with intentional errors...")

    # This code has issues:
    # - calculate_stats calls process_data with wrong number of args
    # - Missing type annotations
    broken_code = '''"""Data processing module with errors."""

def process_data(data: list, threshold: int) -> list:
    """Process data with threshold."""
    return [x for x in data if x > threshold]


def calculate_stats(values):
    """Calculate statistics (has errors)."""
    # ERROR: process_data needs 2 args but we only pass 1
    processed = process_data(values)
    return {
        "count": len(processed),
        "sum": sum(processed)
    }


def format_results(stats: dict) -> str:
    """Format statistics."""
    return f"Count: {stats['count']}, Sum: {stats['sum']}"
'''

    edit_path = "/app/examples/broken_code.py"

    response = requests.post(
        f"{BASE_URL}/session/{session_id}/edit",
        json={
            "file_path": edit_path,
            "new_content": broken_code
        }
    )
    response.raise_for_status()
    pretty_print("Edit Added", response.json())

    # Step 3: Apply edits
    print("\nStep 3: Applying edits to filesystem...")
    response = requests.post(f"{BASE_URL}/session/{session_id}/apply")
    response.raise_for_status()
    pretty_print("Edits Applied", response.json())

    # Step 4: Validate the session
    print("\nStep 4: Validating changes...")
    response = requests.post(
        f"{BASE_URL}/session/{session_id}/validate",
        json={"reindex_path": "/app/examples"}
    )
    response.raise_for_status()
    validation_result = response.json()
    pretty_print("Validation Result", {
        "session_id": validation_result["session_id"],
        "status": validation_result["status"],
        "safe_to_commit": validation_result["safe_to_commit"],
        "violation_count": validation_result["violation_count"],
        "violations_summary": [
            {
                "type": v["violation_type"],
                "severity": v["severity"],
                "message": v["message"],
                "location": f"{v.get('file_path', 'unknown')}:{v.get('line_number', '?')}"
            }
            for v in validation_result["violations"][:5]
        ]
    })

    # Step 5: Get detailed fix suggestions
    if not validation_result["safe_to_commit"]:
        print("\nStep 5: Getting fix suggestions...")
        response = requests.get(f"{BASE_URL}/session/{session_id}/violations")
        response.raise_for_status()
        violations = response.json()

        print("\nDetailed Violations and Fixes:")
        for i, v in enumerate(violations, 1):
            print(f"\n--- Violation {i} ---")
            print(f"Type: {v['violation_type']}")
            print(f"Severity: {v['severity']}")
            print(f"Message: {v['message']}")
            print(f"Location: {v.get('file_path')}:{v.get('line_number')}")

            if v.get('code_snippet'):
                print(f"\nCode Snippet:")
                print(v['code_snippet'])

            if v.get('fix_code'):
                print(f"\nSuggested Fix Code:")
                print(v['fix_code'])

            print()

        # Step 6: Apply fixes
        print("\nStep 6: Applying fixes...")

        # Fixed code with corrections
        fixed_code = '''"""Data processing module - FIXED."""

def process_data(data: list, threshold: int) -> list:
    """Process data with threshold."""
    return [x for x in data if x > threshold]


def calculate_stats(values: list) -> dict:
    """Calculate statistics - FIXED."""
    # FIXED: Added missing threshold argument
    processed = process_data(values, threshold=0)
    return {
        "count": len(processed),
        "sum": sum(processed)
    }


def format_results(stats: dict) -> str:
    """Format statistics."""
    return f"Count: {stats['count']}, Sum: {stats['sum']}"
'''

        # Create new session for the fix
        response = requests.post(
            f"{BASE_URL}/session/prepare",
            json={"description": "Fix validation errors"}
        )
        response.raise_for_status()
        fix_session_id = response.json()["session_id"]

        # Add the fix
        response = requests.post(
            f"{BASE_URL}/session/{fix_session_id}/edit",
            json={
                "file_path": edit_path,
                "new_content": fixed_code
            }
        )
        response.raise_for_status()

        # Apply the fix
        response = requests.post(f"{BASE_URL}/session/{fix_session_id}/apply")
        response.raise_for_status()

        # Validate the fix
        print("\nStep 7: Validating fixes...")
        response = requests.post(
            f"{BASE_URL}/session/{fix_session_id}/validate",
            json={"reindex_path": "/app/examples"}
        )
        response.raise_for_status()
        fix_validation = response.json()
        pretty_print("Fix Validation Result", {
            "session_id": fix_validation["session_id"],
            "status": fix_validation["status"],
            "safe_to_commit": fix_validation["safe_to_commit"],
            "violation_count": fix_validation["violation_count"]
        })

        # Step 8: Commit if validation passes
        if fix_validation["safe_to_commit"]:
            print("\nStep 8: Committing changes...")
            response = requests.post(f"{BASE_URL}/session/{fix_session_id}/commit")
            response.raise_for_status()
            pretty_print("Commit Result", response.json())
        else:
            print("\nStep 8: Still have violations, rolling back...")
            response = requests.post(f"{BASE_URL}/session/{fix_session_id}/rollback")
            response.raise_for_status()
            pretty_print("Rollback Result", response.json())

        # Rollback original broken session
        response = requests.post(f"{BASE_URL}/session/{session_id}/rollback")
        response.raise_for_status()

    print("\n" + "="*80)
    print("WORKFLOW DEMONSTRATION COMPLETE")
    print("="*80)


def test_mcp_workflow():
    """Test the MCP tool workflow."""

    print("\n" + "="*80)
    print("MCP (MODEL CONTEXT PROTOCOL) WORKFLOW DEMONSTRATION")
    print("="*80)

    # Step 1: Get available MCP tools
    print("\nStep 1: Getting available MCP tools...")
    response = requests.get(f"{BASE_URL}/mcp/tools")
    response.raise_for_status()
    tools_data = response.json()
    pretty_print("Available MCP Tools", {
        "server_info": tools_data["server_info"],
        "tools": [
            {
                "name": tool["name"],
                "description": tool["description"]
            }
            for tool in tools_data["tools"]
        ]
    })

    # Step 2: Prepare session via MCP
    print("\nStep 2: Preparing edit session via MCP...")
    response = requests.post(
        f"{BASE_URL}/mcp/execute",
        json={
            "name": "prepare_edit_session",
            "arguments": {
                "description": "Testing MCP workflow"
            }
        }
    )
    response.raise_for_status()
    result = response.json()
    session_info = json.loads(result["content"][0]["text"])
    session_id = session_info["session_id"]
    pretty_print("MCP: Session Prepared", session_info)

    # Step 3: Apply and validate edit via MCP
    print("\nStep 3: Applying and validating edit via MCP...")

    test_code = '''"""Test module."""

def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def calculate(x: int, y: int) -> dict:
    """Calculate sum and product."""
    return {
        "sum": add(x, y),
        "product": multiply(x, y)
    }
'''

    response = requests.post(
        f"{BASE_URL}/mcp/execute",
        json={
            "name": "apply_and_validate_edit",
            "arguments": {
                "session_id": session_id,
                "edits": [
                    {
                        "file_path": "/app/examples/mcp_test.py",
                        "new_content": test_code
                    }
                ],
                "reindex_path": "/app/examples"
            }
        }
    )
    response.raise_for_status()
    result = response.json()
    validation_info = json.loads(result["content"][0]["text"])
    pretty_print("MCP: Validation Result", validation_info)

    # Step 4: Commit via MCP if valid
    if validation_info["safe_to_commit"]:
        print("\nStep 4: Committing via MCP...")
        response = requests.post(
            f"{BASE_URL}/mcp/execute",
            json={
                "name": "commit_session",
                "arguments": {
                    "session_id": session_id
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        commit_info = json.loads(result["content"][0]["text"])
        pretty_print("MCP: Commit Result", commit_info)
    else:
        print("\nStep 4: Getting fix suggestions via MCP...")
        response = requests.post(
            f"{BASE_URL}/mcp/execute",
            json={
                "name": "get_fix_suggestions",
                "arguments": {
                    "session_id": session_id
                }
            }
        )
        response.raise_for_status()
        result = response.json()
        fix_info = json.loads(result["content"][0]["text"])
        pretty_print("MCP: Fix Suggestions", fix_info)

    print("\n" + "="*80)
    print("MCP WORKFLOW DEMONSTRATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CODEGRAPH VALIDATION SYSTEM - COMPREHENSIVE TEST")
    print("="*80)
    print("\nThis example demonstrates:")
    print("1. Session-based code editing workflow")
    print("2. Automatic validation against conservation laws")
    print("3. Detailed violation reporting with fix suggestions")
    print("4. MCP (Model Context Protocol) integration for LLMs")
    print("\nPrerequisites:")
    print("- Backend running on http://localhost:8000")
    print("- Neo4j database connected")
    print("- Docker containers up and running")
    print("\n" + "="*80)

    try:
        # Test regular workflow
        test_validation_workflow()

        # Test MCP workflow
        test_mcp_workflow()

        print("\n✅ All tests completed successfully!")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to backend.")
        print("Make sure the backend is running on http://localhost:8000")
        print("Run: docker-compose up -d")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
