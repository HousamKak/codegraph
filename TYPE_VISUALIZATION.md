# Type Visualization - Special Treatment

## Overview

Type relationships are now visualized as **colored borders** around nodes instead of arrows, making type information more prominent and reducing visual clutter.

## Design Rationale

### Why Borders Instead of Arrows?

1. **Intrinsic Property**: Types are properties of elements, not relationships between entities
2. **Reduced Clutter**: Eliminates many edges from the graph (HAS_TYPE, RETURNS_TYPE)
3. **Immediate Recognition**: Type information is visible at a glance
4. **Better Semantics**: Borders represent "belonging to a type" better than arrows
5. **Professional Appearance**: Matches how types are shown in modern IDEs

## Implementation

### 1. Type Edge Extraction

**GraphView.tsx (lines 69-85):**
```typescript
// Extract type information from edges
const typeEdges = graphData.edges.filter(e =>
  e.type === 'HAS_TYPE' || e.type === 'RETURNS_TYPE'
);

// Create a map of node ID to type information
const nodeTypeMap = new Map<string, { typeName: string; typeColor: string }>();

typeEdges.forEach(edge => {
  const typeNode = graphData.nodes.find(n => n.id === edge.target);
  if (typeNode) {
    const typeName = typeNode.properties.name || typeNode.id.split(':').pop() || 'Type';
    const typeColor = EDGE_COLORS[edge.type] || '#64b5f6';
    nodeTypeMap.set(edge.source, { typeName, typeColor });
  }
});
```

### 2. Attaching Type Info to Nodes

**GraphView.tsx (line 95):**
```typescript
const nodes = graphData.nodes.map(n => ({
  ...n,
  id: n.id,
  label: n.properties.name || n.id.split(':').pop() || n.id,
  type: n.labels[0] || 'Unknown',
  x: width / 2 + (Math.random() - 0.5) * 100,
  y: height / 2 + (Math.random() - 0.5) * 100,
  typeInfo: nodeTypeMap.get(n.id), // Attached here
}));
```

### 3. Filtering Type Edges

**GraphView.tsx (lines 112-129):**
```typescript
const links = graphData.edges
  .filter(e => {
    // Skip type edges (they'll be shown as node borders)
    if (e.type === 'HAS_TYPE' || e.type === 'RETURNS_TYPE') {
      return false;
    }
    // ... rest of filtering
  })
```

### 4. Rendering Colored Borders

**GraphView.tsx (lines 222-223):**
```typescript
node.append('circle')
  .attr('r', 20)
  .attr('fill', d => NODE_COLORS[d.type as keyof typeof NODE_COLORS] || '#95a5a6')
  .attr('stroke', (d: any) => d.typeInfo ? d.typeInfo.typeColor : 'none')
  .attr('stroke-width', (d: any) => d.typeInfo ? 3 : 0)
  // ... other attributes
```

### 5. Type Name Labels

**GraphView.tsx (lines 252-262):**
```typescript
// Type labels (below node for typed nodes)
node.filter((d: any) => d.typeInfo)
  .append('text')
  .text((d: any) => `: ${d.typeInfo.typeName}`)
  .attr('text-anchor', 'middle')
  .attr('dy', 30)
  .attr('font-size', '9px')
  .attr('font-weight', '600')
  .attr('fill', (d: any) => d.typeInfo.typeColor)
  .attr('pointer-events', 'none')
  .style('text-shadow', '0 1px 2px rgba(0,0,0,0.8), ...');
```

## Visual Result

### Before (Arrows)
```
┌─────────┐          ┌──────┐
│ myVar   │─HAS_TYPE→│ int  │
└─────────┘          └──────┘
     │
     │ USES
     ↓
┌─────────┐
│ calc()  │
└─────────┘
```

### After (Borders)
```
┌─────────┐
│ myVar   │  (blue border)
│: int    │  (blue text below)
└─────────┘
     │
     │ USES
     ↓
┌─────────┐
│ calc()  │
└─────────┘
```

## Color Scheme

### Type Border Colors

The border color matches the type of relationship:
- **HAS_TYPE**: `#64b5f6` (Blue)
- **RETURNS_TYPE**: `#64b5f6` (Blue)

### Type Node Colors

Type nodes themselves are rendered in:
- **Type**: `#ba68c8` (Purple/Violet) - Changed from blue to distinguish from borders

## Visual Elements

### Nodes with Types
1. **Border**: 3px colored stroke around the node circle
2. **Label**: Type name below the node with colon prefix (`: int`)
3. **Color**: Border and label use the same color (#64b5f6)
4. **Shadow**: Dark text shadow for readability on dark background

### Nodes without Types
1. **No Border**: No stroke on the circle
2. **No Type Label**: Only node name shown

## Data Flow

```
Backend (Neo4j)
    ↓
Edges with HAS_TYPE/RETURNS_TYPE
    ↓
Frontend extracts type edges
    ↓
Maps type info to source nodes
    ↓
Filters out type edges from rendering
    ↓
Renders nodes with colored borders
    ↓
Adds type name labels
```

## Benefits

### 1. Cleaner Graph
- Fewer edges to render
- Less visual clutter
- Easier to follow relationship paths

### 2. Better Type Visibility
- Type information immediately visible
- No need to trace arrows to type nodes
- Color-coded for quick recognition

### 3. Semantic Accuracy
- Types as properties, not relationships
- Matches mental model of typing
- Similar to IDE type hints

### 4. Performance
- Fewer edges to calculate
- Faster force simulation
- Less DOM elements

## Edge Cases

### Multiple Types
Currently, if a node has multiple type edges, only the first one found is displayed. Future enhancement could support multiple types.

### Type Nodes
Type nodes themselves (nodes with label "Type") are still rendered normally but won't have type borders (types don't have types).

### Diff View
Type borders are preserved in diff view:
- Added nodes with types: Green or red fill, blue border
- Modified nodes: Orange fill, blue border (if typed)
- Type changes would show as border color changes

## Files Modified

1. **frontend/src/components/GraphView.tsx**
   - Lines 69-131: Type extraction and filtering
   - Lines 222-223: Border rendering
   - Lines 252-262: Type label rendering

2. **frontend/src/components/DiffView.tsx**
   - Lines 96-143: Type extraction and filtering
   - Lines 240-241: Border rendering
   - Lines 261-271: Type label rendering

3. **frontend/src/types/index.ts**
   - Line 157: Changed Type node color from `#64b5f6` (blue) to `#ba68c8` (purple)

## Configuration

### Customize Type Colors

To change type border colors, edit `EDGE_COLORS` in `frontend/src/types/index.ts`:

```typescript
export const EDGE_COLORS: Record<string, string> = {
  HAS_TYPE: '#64b5f6',        // Change this
  RETURNS_TYPE: '#64b5f6',    // And this
  // ...
};
```

### Customize Border Width

Edit line 223 in GraphView.tsx:
```typescript
.attr('stroke-width', (d: any) => d.typeInfo ? 3 : 0)  // Change 3 to desired width
```

### Customize Type Label Position

Edit line 257 in GraphView.tsx:
```typescript
.attr('dy', 30)  // Change vertical offset from node center
```

## Future Enhancements

1. **Multiple Types**: Support displaying multiple types with multiple borders or stacked labels
2. **Type Hierarchy**: Show inheritance/subtype relationships in border styling
3. **Toggle**: Option to switch between border and arrow visualization
4. **Type Tooltips**: Hover over border to see full type information
5. **Generic Types**: Special visualization for parameterized types (List[int], etc.)
