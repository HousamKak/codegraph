/**
 * Mock graph data for testing
 */

export const mockGraphData = {
  nodes: [
    {
      id: 'func1',
      label: 'calculate_sum',
      type: 'function',
      file_path: '/test/module.py',
      line_number: 10,
      x: 100,
      y: 100,
    },
    {
      id: 'func2',
      label: 'process_data',
      type: 'function',
      file_path: '/test/module.py',
      line_number: 20,
      x: 200,
      y: 200,
    },
    {
      id: 'class1',
      label: 'DataProcessor',
      type: 'class',
      file_path: '/test/processor.py',
      line_number: 5,
      x: 150,
      y: 150,
    },
  ],
  edges: [
    {
      id: 'edge1',
      source: 'func2',
      target: 'func1',
      type: 'calls',
    },
    {
      id: 'edge2',
      source: 'class1',
      target: 'func2',
      type: 'declares',
    },
  ],
}

export const mockValidationReport = {
  structural: {
    violations: [
      {
        type: 'missing_node',
        severity: 'error',
        message: 'Function node not found in graph',
        file_path: '/test/module.py',
        line_number: 15,
      },
    ],
  },
  reference: {
    violations: [],
  },
  typing: {
    violations: [],
  },
}

export const mockCommits = [
  {
    sha: 'abc123',
    message: 'Initial commit',
    author: 'Test Author',
    date: '2024-01-01T00:00:00Z',
  },
  {
    sha: 'def456',
    message: 'Add new feature',
    author: 'Test Author',
    date: '2024-01-02T00:00:00Z',
  },
]
