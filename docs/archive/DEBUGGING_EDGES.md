# Debugging: No Edges Showing in Graph

## ✅ Fixes Applied

1. **Fixed edge property names**: Changed from `from_id`/`to_id` to `source`/`target` (matches backend)
2. **Added edge filtering**: Only show edges where both nodes exist
3. **Added debug logging**: Console will show what's happening

## 🔍 How to Debug

### Step 1: Open Browser Console

1. Open frontend: http://localhost:5173
2. Press **F12** to open DevTools
3. Go to **Console** tab

### Step 2: Check Console Output

You should see logs like:
```
GraphView Debug: {
  totalNodes: 10,
  totalEdges: 12,
  sampleNode: {...},
  sampleEdge: {...},
  nodeIds: [...]
}
Valid links: 12 / 12
```

### Step 3: What the Numbers Mean

**If you see:**
```
totalNodes: 10
totalEdges: 12
Valid links: 12 / 12
```
✅ **All edges are valid** - Graph should show edges

**If you see:**
```
totalNodes: 10
totalEdges: 12
Valid links: 0 / 12
```
❌ **No edges are valid** - Edges reference non-existent nodes

### Step 4: Check Backend Data Structure

I've created a test page. Open it in your browser:
```
file:///D:/dev/graph%20db%20for%20codebase/test_frontend_data.html
```

This will show:
- ✓ Graph endpoint reachable
- ✓ Edge structure (has `source`, `target`, `type`)
- ✓ Node-edge consistency

## 🐛 Common Issues & Solutions

### Issue 1: Edge Structure Wrong

**Symptom:** Console shows edges but they have wrong keys

**Check:** Look at `sampleEdge` in console. Should have:
```javascript
{
  source: "abc123...",
  target: "def456...",
  type: "CALLS",
  properties: {}
}
```

**If it has `from` and `to` instead:** Backend response format changed
**Fix:** Update GraphView line 84-90 to use correct property names

### Issue 2: Nodes Have Wrong IDs

**Symptom:** `Valid links: 0 / 12` (no valid edges)

**Check:**
```javascript
// In console, check if node IDs match edge source/target
const data = await fetch('http://localhost:8000/graph?limit=10').then(r => r.json());
const nodeIds = data.nodes.map(n => n.id);
const edge = data.edges[0];
console.log('Node IDs:', nodeIds);
console.log('Edge source:', edge.source, 'exists?', nodeIds.includes(edge.source));
console.log('Edge target:', edge.target, 'exists?', nodeIds.includes(edge.target));
```

**If IDs don't match:** Backend might be returning edges for nodes not in the result set
**Fix:** Increase limit in API call or fix backend to return all referenced nodes

### Issue 3: Backend Returns No Edges

**Symptom:** `totalEdges: 0`

**Check backend directly:**
```bash
curl http://localhost:8000/graph?limit=100 | jq '.edges | length'
```

**If it returns 0:** Database has no relationships
**Fix:** Re-index your codebase:
```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "D:\\dev\\graph db for codebase\\backend\\examples\\example_code.py", "clear": false}'
```

### Issue 4: D3 Not Drawing Lines

**Symptom:** Console shows valid links but no visual edges

**Check:** Look at browser's element inspector (F12 → Elements)
- Find `<svg>` element
- Look inside for `<g class="links">`
- Check if there are `<line>` elements

**If lines exist but invisible:**
- Check stroke color
- Check opacity
- Check if lines are off-screen

**Fix:** Try clicking "Re-layout" button

## 📊 Expected Data Flow

```
1. App.tsx loads
   ↓
2. React Query fetches: api.getGraph(1000)
   ↓
3. API client calls: GET http://localhost:8000/graph?limit=1000
   ↓
4. Backend returns: { nodes: [...], edges: [...] }
   ↓
5. Store updates: setGraphData(data)
   ↓
6. GraphView receives data via: useStore().graphData
   ↓
7. GraphView processes:
   - Creates node array with IDs
   - Filters edges (keeps only valid ones)
   - Creates D3 force simulation
   - Draws nodes and edges
   ↓
8. Graph displays with edges visible
```

## 🔬 Manual Test Commands

### Test 1: Backend Responding?
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy",...}
```

### Test 2: Graph Has Data?
```bash
curl http://localhost:8000/graph?limit=10
# Should return: {"nodes":[...],"edges":[...]}
```

### Test 3: Count Edges
```bash
curl -s http://localhost:8000/graph?limit=100 | jq '.edges | length'
# Should return: number > 0
```

### Test 4: Check Edge Structure
```bash
curl -s http://localhost:8000/graph?limit=10 | jq '.edges[0]'
# Should show: {"source":"...","target":"...","type":"..."}
```

### Test 5: Verify Node-Edge Match
```bash
curl -s http://localhost:8000/graph?limit=10 | jq '{
  node_ids: [.nodes[].id],
  edge_sources: [.edges[].source],
  edge_targets: [.edges[].target]
}'
# All edge sources/targets should be in node_ids list
```

## 🎯 Quick Fixes

### If Still No Edges After All Fixes:

1. **Hard refresh browser**: Ctrl+Shift+R (clears React Query cache)

2. **Increase limit in App.tsx**:
```typescript
// Change line 29
queryFn: () => api.getGraph(10000),  // Increased from 1000
```

3. **Check backend logs** for errors:
```bash
# Check terminal where backend is running
# Look for any error messages
```

4. **Re-index the codebase**:
```bash
curl -X POST http://localhost:8000/index \
  -H "Content-Type: application/json" \
  -d '{"path": "D:\\dev\\graph db for codebase\\backend", "clear": true}'
```

5. **Restart everything**:
```bash
# Terminal 1: Restart Neo4j
docker restart codegraph-neo4j

# Terminal 2: Restart Backend
# Ctrl+C, then:
python run.py

# Terminal 3: Restart Frontend
# Ctrl+C, then:
npm run dev
```

## 📝 What You Should See in Console

**Good output:**
```
GraphView Debug: {
  totalNodes: 10,
  totalEdges: 51,
  sampleNode: {id: "fef50208f048c8a8", labels: ["Module"], ...},
  sampleEdge: {source: "fef50208f048c8a8", target: "2b7847495c198d4a", type: "CONTAINS", ...},
  nodeIds: ["fef50208f048c8a8", "2b7847495c198d4a", ...]
}
Valid links: 51 / 51
```

**Bad output:**
```
GraphView Debug: {
  totalNodes: 10,
  totalEdges: 51,
  sampleNode: {id: "fef50208f048c8a8", ...},
  sampleEdge: {source: "xyz999", target: "abc000", type: "CONTAINS", ...},
  nodeIds: ["fef50208f048c8a8", "2b7847495c198d4a", ...]
}
Invalid edge: {...} source exists: false target exists: false
Invalid edge: {...} source exists: false target exists: false
...
Valid links: 0 / 51
```

## ✅ Confirmation Tests

**Test edges are drawing:**
1. Open browser inspector (F12 → Elements)
2. Find: `<svg class="w-full h-full">`
3. Inside, find: `<g class="links">`
4. Should see multiple `<line>` elements
5. Each line should have `stroke="color"` and `marker-end="url(...)"`

**Test edge labels:**
1. In same `<g class="links">`, look for `<text>` elements
2. Each text should contain relationship type (CALLS, CONTAINS, etc.)
3. Check `x`, `y` coordinates are within viewport

## 🆘 If Still Broken

1. Share console output (copy all logs)
2. Share backend response:
   ```bash
   curl http://localhost:8000/graph?limit=10 > graph_response.json
   ```
3. Check if D3 simulation is running:
   ```javascript
   // In browser console
   d3.select('svg').selectAll('line').size()
   // Should return number > 0
   ```

---

**Current Status:** Edges should now be visible after the `source`/`target` fix. Check console for debug output!
