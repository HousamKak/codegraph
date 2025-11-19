# Frontend-Backend API Integration

This document describes how the frontend and backend are connected and the API format fixes that were applied.

## API Base URL

The frontend connects to the backend via:
```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

Configured in `frontend/.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

## API Response Format Fixes

### 1. Snapshots Endpoint
**Backend Response:**
```json
{
  "snapshots": [...],
  "count": 5
}
```

**Frontend Fix:**
```typescript
async listSnapshots(): Promise<Snapshot[]> {
  const response: any = await this.fetch('/snapshots');
  return response.snapshots || [];  // Extract array from wrapper
}
```

### 2. Compare Snapshots Endpoint
**Backend Format:** ✅ Matches frontend expectations
```json
{
  "old_snapshot_id": "...",
  "new_snapshot_id": "...",
  "summary": {
    "nodes_added": 5,
    "nodes_removed": 2,
    ...
  },
  "nodes": {
    "added": [...],  // Full node objects
    "removed": [...],
    "modified": [...]
  },
  "edges": { ... }
}
```

### 3. Validation Endpoint
**Backend Response:**
```json
{
  "total_violations": 10,
  "errors": 5,
  "warnings": 5,
  "by_type": {...},
  "summary": {
    "signature_conservation": 2,
    "reference_integrity": 3,
    ...
  },
  "violations": [...]  // Single array of all violations
}
```

**Frontend Fix:**
ValidationView now groups violations by conservation law:
```typescript
const s_law_violations = validation.violations.filter(v =>
  v.violation_type.includes('structural') ||
  v.violation_type.includes('schema') ||
  v.violation_type === 'edge_type_invalid'
);
```

### 4. Query Endpoint
**Backend Response:** Raw Neo4j results as array
```json
[
  {"n": {...}, "r": {...}},
  {"n": {...}, "r": {...}}
]
```

**Frontend Fix:**
```typescript
const response = await api.executeQuery(query);
setResult(Array.isArray(response) ? response : []);

// Then render dynamically based on first row keys
{Object.keys(result[0]).map((col) => (...))}
```

## Endpoint Mappings

| Frontend Method | Backend Endpoint | Method | Notes |
|----------------|------------------|--------|-------|
| `getGraph()` | `/graph?limit=N` | GET | Returns nodes and edges |
| `listSnapshots()` | `/snapshots` | GET | Returns wrapper object |
| `createSnapshot()` | `/snapshot/create?description=...` | POST | Returns snapshot_id |
| `getSnapshot()` | `/snapshot/{id}` | GET | Returns snapshot details |
| `compareSnapshots()` | `/snapshot/compare?old_snapshot_id=...&new_snapshot_id=...` | POST | Returns diff |
| `executeQuery()` | `/query` | POST | Body: `{query, parameters?}` |
| `validate()` | `/validate` | GET | Returns validation report |
| `getStatistics()` | `/stats` | GET | Returns node/edge counts |

## Graph Data Format

### Node Structure
```typescript
{
  id: string,
  labels: string[],  // e.g., ["Function"]
  properties: {
    name: string,
    qualified_name?: string,
    file_path?: string,
    line_number?: number,
    changed?: boolean,
    ...
  }
}
```

### Edge Structure
```typescript
{
  id?: string,
  source: string,      // from_id
  target: string,      // to_id
  type: string,        // edge type (CALLS, CONTAINS, etc.)
  properties?: {...}
}
```

## CORS Configuration

Backend allows all origins in development:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Error Handling

All API methods throw errors that are caught by components:
```typescript
try {
  const result = await api.someMethod();
  // handle success
} catch (err: any) {
  setError(err.message || 'Operation failed');
}
```

## Testing API Integration

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Get Statistics
```bash
curl http://localhost:8000/stats
```

### 3. List Snapshots
```bash
curl http://localhost:8000/snapshots
```

### 4. Execute Query
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "MATCH (n) RETURN n LIMIT 5"}'
```

### 5. Validate Graph
```bash
curl http://localhost:8000/validate
```

## Common Issues & Solutions

### Issue: "snapshots is not iterable"
**Cause:** Backend returns `{snapshots: [...], count: N}`, not a direct array

**Solution:** Extract array: `response.snapshots || []`

### Issue: "Cannot read property 's_law_violations'"
**Cause:** Backend returns single `violations` array, not grouped by law

**Solution:** Filter violations by type in component

### Issue: Query results not displaying
**Cause:** Backend returns raw array, frontend expected structured format

**Solution:** Use dynamic column extraction from first row

### Issue: CORS errors
**Cause:** Backend not allowing frontend origin

**Solution:** Configure CORS in `backend/app/main.py`

## Backend Logs

Monitor backend activity:
```bash
# All requests are logged with status codes
INFO: 127.0.0.1:xxxxx - "GET /graph?limit=1000 HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "GET /snapshots HTTP/1.1" 200 OK
INFO: 127.0.0.1:xxxxx - "POST /query HTTP/1.1" 200 OK
```

## Frontend State Management

Using Zustand for global state:
```typescript
interface AppState {
  currentView: 'graph' | 'diff' | 'validate' | 'query';
  graphData: GraphData | null;
  snapshots: Snapshot[];
  selectedSnapshot: string | null;
  compareSnapshots: [string, string] | null;
  selectedNode: Node | null;
  selectedEdge: Edge | null;
  // ...actions
}
```

## Performance Considerations

1. **Graph Limiting:** Default limit of 1000 nodes to prevent browser freeze
2. **Query Pagination:** Consider implementing for large result sets
3. **Debouncing:** Query input debounced to reduce API calls
4. **Caching:** React Query (TanStack Query) handles request caching

## Next Steps

- [ ] Add authentication/authorization
- [ ] Implement WebSocket for real-time updates
- [ ] Add query result pagination
- [ ] Implement graph filtering UI
- [ ] Add export functionality (JSON, CSV)
- [ ] Optimize graph rendering for large datasets
