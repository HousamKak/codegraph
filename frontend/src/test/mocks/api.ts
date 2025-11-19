/**
 * MSW API mocks for testing
 */
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

const baseUrl = 'http://localhost:8000'

/**
 * Mock API handlers
 */
export const handlers = [
  // Graph API
  http.get(`${baseUrl}/api/graph`, () => {
    return HttpResponse.json({
      nodes: [
        { id: '1', label: 'test_function', type: 'function', x: 0, y: 0 },
        { id: '2', label: 'test_class', type: 'class', x: 100, y: 100 },
      ],
      edges: [
        { id: 'e1', source: '1', target: '2', type: 'calls' },
      ],
    })
  }),

  // Statistics API
  http.get(`${baseUrl}/api/graph/stats`, () => {
    return HttpResponse.json({
      total_nodes: 2,
      total_edges: 1,
      node_types: { function: 1, class: 1 },
      edge_types: { calls: 1 },
    })
  }),

  // Validation API
  http.get(`${baseUrl}/api/validate`, () => {
    return HttpResponse.json({
      structural: { violations: [] },
      reference: { violations: [] },
      typing: { violations: [] },
    })
  }),

  // Snapshots API
  http.get(`${baseUrl}/api/snapshots`, () => {
    return HttpResponse.json([
      {
        id: 'snap1',
        name: 'Test Snapshot',
        created_at: '2024-01-01T00:00:00Z',
      },
    ])
  }),

  http.post(`${baseUrl}/api/snapshots`, () => {
    return HttpResponse.json({
      id: 'snap2',
      name: 'New Snapshot',
      created_at: '2024-01-02T00:00:00Z',
    })
  }),

  // Git API
  http.get(`${baseUrl}/api/git/commits`, () => {
    return HttpResponse.json([
      {
        sha: 'abc123',
        message: 'Test commit',
        author: 'Test Author',
        date: '2024-01-01T00:00:00Z',
      },
    ])
  }),

  // Files API
  http.get(`${baseUrl}/api/files`, () => {
    return HttpResponse.json([
      { path: 'test.py', type: 'file' },
      { path: 'module/', type: 'directory' },
    ])
  }),
]

/**
 * MSW server instance
 */
export const server = setupServer(...handlers)
