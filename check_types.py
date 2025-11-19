import requests
import json

# Fetch graph data
response = requests.get('http://localhost:8000/graph?limit=100')
data = response.json()

# Create node lookup
nodes = {n['id']: n for n in data['nodes']}

# Find type edges
type_edges = [e for e in data['edges'] if 'TYPE' in e['type']]

print(f'Total type edges: {len(type_edges)}\n')

# Group by source node type
from collections import defaultdict
by_node_type = defaultdict(list)

for edge in type_edges:
    source_node = nodes.get(edge['source'])
    if source_node:
        node_label = source_node['labels'][0] if source_node['labels'] else 'Unknown'
        by_node_type[node_label].append(edge)

print('Type edges by node type:')
for node_type, edges in sorted(by_node_type.items()):
    print(f'  {node_type}: {len(edges)} edges')

print('\n\nDetailed breakdown:')
for node_type, edges in sorted(by_node_type.items()):
    print(f'\n{node_type} nodes with types:')
    for edge in edges[:5]:  # Show first 5
        source_node = nodes.get(edge['source'])
        target_node = nodes.get(edge['target'])
        source_name = source_node.get('properties', {}).get('name', 'unnamed')
        target_name = target_node.get('properties', {}).get('name', 'unknown') if target_node else 'unknown'
        print(f'  {edge["type"]}: {source_name} -> {target_name}')

# Check for Variable nodes
print('\n\nVariable nodes:')
variables = [n for n in data['nodes'] if 'Variable' in n['labels']]
print(f'Total variables: {len(variables)}')
for var in variables[:5]:
    var_id = var['id']
    var_name = var.get('properties', {}).get('name', 'unnamed')
    has_type = any(e['source'] == var_id and 'TYPE' in e['type'] for e in data['edges'])
    print(f'  {var_name}: has_type={has_type}')
