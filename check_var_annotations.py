import requests

# Fetch graph data
response = requests.get('http://localhost:8000/graph?limit=100')
data = response.json()

# Find variables
variables = [n for n in data['nodes'] if 'Variable' in n['labels']]

print(f'Total variables: {len(variables)}\n')

print('Variable details:')
for var in variables:
    props = var.get('properties', {})
    name = props.get('name', 'unnamed')
    type_ann = props.get('type_annotation', None)
    print(f'  {name}: type_annotation={type_ann}')
