#!/usr/bin/env python3
"""Test MCP server tools to ensure all fixes are applied."""

import json
import subprocess
import sys

def test_mcp_tool(tool_name: str, arguments: dict = None):
    """Test an MCP tool by sending a request."""
    if arguments is None:
        arguments = {}

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }

    # Start MCP server
    proc = subprocess.Popen(
        [sys.executable, "backend/codegraph/mcp_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Send request
    request_line = json.dumps(request) + "\n"
    stdout, stderr = proc.communicate(input=request_line, timeout=10)

    # Parse response
    lines = stdout.strip().split("\n")
    for line in lines:
        if line.strip() and not line.startswith("INFO:"):
            try:
                response = json.loads(line)
                if "result" in response:
                    return response["result"]
            except json.JSONDecodeError:
                continue

    return None

if __name__ == "__main__":
    print("Testing MCP Server Tools...")
    print("=" * 60)

    # Test 1: Index codebase
    print("\n1. Testing index_codebase tool...")
    result = test_mcp_tool("index_codebase", {
        "path": "/app/examples/connected_example.py",
        "clear": True
    })
    if result:
        print(f"✅ Index successful: {result.get('content', [{}])[0].get('text', '')[:100]}...")
    else:
        print("❌ Index failed")

    # Test 2: Get stats
    print("\n2. Testing get_graph_stats tool...")
    result = test_mcp_tool("get_graph_stats", {})
    if result:
        print(f"✅ Stats retrieved: {result.get('content', [{}])[0].get('text', '')[:100]}...")
    else:
        print("❌ Stats failed")

    # Test 3: Validate
    print("\n3. Testing validate_codebase tool...")
    result = test_mcp_tool("validate_codebase", {})
    if result:
        print(f"✅ Validation completed: {result.get('content', [{}])[0].get('text', '')[:100]}...")
    else:
        print("❌ Validation failed")

    print("\n" + "=" * 60)
    print("MCP Server Testing Complete!")
