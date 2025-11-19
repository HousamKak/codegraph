/**
 * Unit tests for API Client
 */
import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { ApiClient, ApiError } from '@/api/client'

const baseUrl = 'http://localhost:8000'

// Mock server setup
const server = setupServer()

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('ApiClient', () => {
  const client = new ApiClient()

  describe('Graph Operations', () => {
    it('should fetch full graph', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return HttpResponse.json({
            nodes: [{ id: '1', label: 'test', type: 'function' }],
            edges: [],
          })
        })
      )

      const graph = await client.getGraph()

      expect(graph).toHaveProperty('nodes')
      expect(graph).toHaveProperty('edges')
      expect(graph.nodes).toHaveLength(1)
    })

    it('should fetch graph with limit', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, ({ request }) => {
          const url = new URL(request.url)
          const limit = url.searchParams.get('limit')

          expect(limit).toBe('10')

          return HttpResponse.json({
            nodes: [],
            edges: [],
          })
        })
      )

      await client.getGraph(10)
    })

    it('should execute cypher query', async () => {
      server.use(
        http.post(`${baseUrl}/graph/query`, async ({ request }) => {
          const body = await request.json() as any

          expect(body).toHaveProperty('query')
          expect(body.query).toBe('MATCH (n) RETURN n')

          return HttpResponse.json({
            columns: ['n'],
            data: [],
          })
        })
      )

      const result = await client.executeQuery('MATCH (n) RETURN n')

      expect(result).toHaveProperty('columns')
      expect(result).toHaveProperty('data')
    })

    it('should get node by id', async () => {
      const nodeId = 'test-node-123'

      server.use(
        http.get(`${baseUrl}/graph/node/${nodeId}`, () => {
          return HttpResponse.json({
            nodes: [{ id: nodeId, label: 'test', type: 'function' }],
            edges: [],
          })
        })
      )

      const graph = await client.getNodeById(nodeId)

      expect(graph.nodes).toHaveLength(1)
      expect(graph.nodes[0].id).toBe(nodeId)
    })

    it('should get node neighbors', async () => {
      const nodeId = 'test-node'

      server.use(
        http.get(`${baseUrl}/graph/node/${nodeId}/neighbors`, () => {
          return HttpResponse.json({
            nodes: [
              { id: nodeId, label: 'center', type: 'function' },
              { id: 'neighbor1', label: 'neighbor', type: 'function' },
            ],
            edges: [
              { id: 'e1', source: nodeId, target: 'neighbor1', type: 'calls' },
            ],
          })
        })
      )

      const graph = await client.getNodeNeighbors(nodeId)

      expect(graph.nodes.length).toBeGreaterThan(1)
      expect(graph.edges).toHaveLength(1)
    })

    it('should get node neighbors with depth', async () => {
      server.use(
        http.get(`${baseUrl}/graph/node/test/neighbors`, ({ request }) => {
          const url = new URL(request.url)
          const depth = url.searchParams.get('depth')

          expect(depth).toBe('2')

          return HttpResponse.json({ nodes: [], edges: [] })
        })
      )

      await client.getNodeNeighbors('test', 2)
    })
  })

  describe('Statistics', () => {
    it('should fetch graph statistics', async () => {
      server.use(
        http.get(`${baseUrl}/graph/statistics`, () => {
          return HttpResponse.json({
            total_nodes: 100,
            total_edges: 50,
            functions: 60,
            classes: 40,
          })
        })
      )

      const stats = await client.getStatistics()

      expect(stats).toHaveProperty('total_nodes')
      expect(stats.total_nodes).toBe(100)
    })
  })

  describe('Snapshot Operations', () => {
    it('should list all snapshots', async () => {
      server.use(
        http.get(`${baseUrl}/snapshots`, () => {
          return HttpResponse.json({
            snapshots: [
              { id: 'snap1', description: 'Test', created_at: '2024-01-01' },
              { id: 'snap2', description: 'Test 2', created_at: '2024-01-02' },
            ],
            count: 2,
          })
        })
      )

      const snapshots = await client.listSnapshots()

      expect(snapshots).toHaveLength(2)
      expect(snapshots[0].id).toBe('snap1')
    })

    it('should create snapshot', async () => {
      server.use(
        http.post(`${baseUrl}/snapshots/create`, ({ request }) => {
          const url = new URL(request.url)
          const description = url.searchParams.get('description')

          expect(description).toBe('Test Snapshot')

          return HttpResponse.json({
            snapshot_id: 'new-snap-123',
          })
        })
      )

      const result = await client.createSnapshot('Test Snapshot')

      expect(result).toHaveProperty('snapshot_id')
      expect(result.snapshot_id).toBe('new-snap-123')
    })

    it('should get snapshot details', async () => {
      server.use(
        http.get(`${baseUrl}/snapshots/snap1`, () => {
          return HttpResponse.json({
            id: 'snap1',
            description: 'Test',
            created_at: '2024-01-01',
            stats: { nodes: 10, edges: 5 },
          })
        })
      )

      const snapshot = await client.getSnapshot('snap1')

      expect(snapshot.id).toBe('snap1')
      expect(snapshot).toHaveProperty('stats')
    })

    it('should delete snapshot', async () => {
      server.use(
        http.delete(`${baseUrl}/snapshots/snap1`, () => {
          return new HttpResponse(null, { status: 204 })
        })
      )

      await expect(client.deleteSnapshot('snap1')).resolves.toBeUndefined()
    })

    it('should get snapshot graph', async () => {
      server.use(
        http.get(`${baseUrl}/snapshots/snap1/graph`, () => {
          return HttpResponse.json({
            nodes: [{ id: '1', label: 'test', type: 'function' }],
            edges: [],
          })
        })
      )

      const graph = await client.getSnapshotGraph('snap1')

      expect(graph).toHaveProperty('nodes')
      expect(graph.nodes).toHaveLength(1)
    })
  })

  describe('Error Handling', () => {
    it('should handle 404 errors', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return new HttpResponse('Not found', { status: 404 })
        })
      )

      await expect(client.getGraph()).rejects.toThrow(ApiError)
      await expect(client.getGraph()).rejects.toThrow('Not found')
    })

    it('should handle 500 errors', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return new HttpResponse('Internal server error', { status: 500 })
        })
      )

      try {
        await client.getGraph()
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError)
        expect((error as ApiError).status).toBe(500)
      }
    })

    it('should handle network errors', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return HttpResponse.error()
        })
      )

      await expect(client.getGraph()).rejects.toThrow()
    })

    it('should throw ApiError with details', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return new HttpResponse('Detailed error message', { status: 400 })
        })
      )

      try {
        await client.getGraph()
        expect.fail('Should have thrown')
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError)
        expect((error as ApiError).message).toBe('Detailed error message')
        expect((error as ApiError).status).toBe(400)
      }
    })
  })

  describe('Request/Response Handling', () => {
    it('should set correct headers', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, ({ request }) => {
          expect(request.headers.get('Content-Type')).toBe('application/json')
          return HttpResponse.json({ nodes: [], edges: [] })
        })
      )

      await client.getGraph()
    })

    it('should parse JSON responses', async () => {
      server.use(
        http.get(`${baseUrl}/graph`, () => {
          return HttpResponse.json({ nodes: [], edges: [] })
        })
      )

      const result = await client.getGraph()

      expect(result).toBeInstanceOf(Object)
      expect(result).toHaveProperty('nodes')
    })

    it('should handle query parameters', async () => {
      server.use(
        http.get(`${baseUrl}/graph/node/test/neighbors`, ({ request }) => {
          const url = new URL(request.url)
          expect(url.searchParams.has('depth')).toBe(true)
          return HttpResponse.json({ nodes: [], edges: [] })
        })
      )

      await client.getNodeNeighbors('test', 1)
    })
  })
})
