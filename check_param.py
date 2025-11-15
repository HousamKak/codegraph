#!/usr/bin/env python3
"""Check parameter default values."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from codegraph.db import CodeGraphDB

# Connect to Neo4j
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"

db = CodeGraphDB(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)

# Query for calculate_total function parameters
query = """
MATCH (f:Function {name: 'calculate_total'})-[:HAS_PARAMETER]->(p:Parameter)
RETURN f.qualified_name as func, p.name as param_name, p.position as position,
       p.default_value as default_value, p.type_annotation as type
ORDER BY f.qualified_name, p.position
"""

with db.driver.session() as session:
    result = session.run(query)
    print("Parameters for calculate_total:")
    print("="*80)
    for record in result:
        print(f"Function: {record['func']}")
        print(f"  Parameter: {record['param_name']}")
        print(f"  Position: {record['position']}")
        print(f"  Type: {record['type']}")
        print(f"  Default: {record['default_value']}")
        print()

db.close()
