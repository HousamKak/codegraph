"""Test script demonstrating CodeGraph usage."""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from codegraph import CodeGraphDB, PythonParser, GraphBuilder, QueryInterface, ConservationValidator


def main():
    """Main test function."""
    print("=" * 60)
    print("CodeGraph Demo - Conservation Laws for Code Integrity")
    print("=" * 60)

    # Connect to Neo4j
    print("\n1. Connecting to Neo4j...")
    db = CodeGraphDB(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

    # Clear and initialize
    print("2. Initializing database...")
    db.clear_database()
    db.initialize_schema()

    # Parse example code
    print("\n3. Parsing example Python files...")
    parser = PythonParser()

    example_file = os.path.join(os.path.dirname(__file__), "example_code.py")
    entities1, relationships1 = parser.parse_file(example_file)
    print(f"   - example_code.py: {len(entities1)} entities, {len(relationships1)} relationships")

    violations_file = os.path.join(os.path.dirname(__file__), "example_violations.py")
    entities2, relationships2 = parser.parse_file(violations_file)
    print(f"   - example_violations.py: {len(entities2)} entities, {len(relationships2)} relationships")

    # Combine entities and relationships
    all_entities = {**entities1, **entities2}
    all_relationships = relationships1 + relationships2

    # Build graph
    print("\n4. Building graph in Neo4j...")
    builder = GraphBuilder(db)
    builder.build_graph(all_entities, all_relationships)

    # Show statistics
    print("\n5. Database Statistics:")
    stats = db.get_statistics()
    for node_type, count in stats.items():
        print(f"   - {node_type}: {count}")

    # Query examples
    print("\n6. Query Examples:")
    query = QueryInterface(db)

    # Find all functions
    functions = query.find_function()
    print(f"\n   a) Total functions in codebase: {len(functions)}")

    # Find specific function
    calc_funcs = query.find_function(name="calculate_average")
    if calc_funcs:
        func = calc_funcs[0]
        print(f"\n   b) Found function: {func['qualified_name']}")
        print(f"      Signature: {func['signature']}")

        # Get signature details
        sig_info = query.get_function_signature(func['id'])
        if sig_info:
            print(f"      Parameters: {len(sig_info['parameters'])}")
            for param_info in sig_info['parameters']:
                param = param_info['param']
                print(f"        - {param['name']}: {param.get('type_annotation', 'no type')}")

        # Find callers
        callers = query.find_callers(func['id'])
        print(f"      Called by: {len(callers)} functions")
        for caller_info in callers:
            caller = caller_info['caller']
            print(f"        - {caller['qualified_name']}")

        # Find callees
        callees = query.find_callees(func['id'])
        print(f"      Calls: {len(callees)} functions")
        for callee_info in callees:
            callee = callee_info['callee']
            print(f"        - {callee['qualified_name']}")

    # Search for Calculator class
    calc_classes = query.search_by_pattern("Calculator", entity_type="Class")
    if calc_classes:
        print(f"\n   c) Found {len(calc_classes)} Calculator class(es)")
        for result in calc_classes:
            node = result['node']
            print(f"      - {node['qualified_name']}")

    # Find orphaned nodes
    orphans = query.find_orphaned_nodes()
    print(f"\n   d) Orphaned nodes: {len(orphans)}")

    # Validate conservation laws
    print("\n" + "=" * 60)
    print("7. Conservation Law Validation")
    print("=" * 60)

    validator = ConservationValidator(db)
    report = validator.get_validation_report()

    print(f"\nTotal Violations: {report['total_violations']}")
    print(f"  - Errors: {report['errors']}")
    print(f"  - Warnings: {report['warnings']}")

    print("\nViolations by Conservation Law:")
    print(f"  1. Signature Conservation: {report['summary']['signature_conservation']}")
    print(f"  2. Reference Integrity: {report['summary']['reference_integrity']}")
    print(f"  3. Data Flow Consistency: {report['summary']['data_flow_consistency']}")
    print(f"  4. Structural Integrity: {report['summary']['structural_integrity']}")

    # Display violations
    if report['violations']:
        print("\n" + "-" * 60)
        print("Detailed Violations:")
        print("-" * 60)

        for i, violation in enumerate(report['violations'][:10], 1):
            print(f"\n{i}. [{violation.severity.upper()}] {violation.message}")
            print(f"   Type: {violation.violation_type.value}")
            if violation.suggested_fix:
                print(f"   Fix: {violation.suggested_fix}")

        if len(report['violations']) > 10:
            print(f"\n... and {len(report['violations']) - 10} more violations")

    # Impact analysis example
    print("\n" + "=" * 60)
    print("8. Impact Analysis Example")
    print("=" * 60)

    calc_total_funcs = query.find_function(name="calculate_total")
    if calc_total_funcs:
        func_id = calc_total_funcs[0]['id']
        impact = query.get_impact_analysis(func_id, "delete")

        print(f"\nImpact of deleting 'calculate_total':")
        print(f"  - Would affect {len(impact['affected_callers'])} callers")
        for caller_info in impact['affected_callers']:
            caller = caller_info['caller']
            print(f"    - {caller['qualified_name']}")

    # Close database connection
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    db.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure Neo4j is running:")
        print("  docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest")
        sys.exit(1)
