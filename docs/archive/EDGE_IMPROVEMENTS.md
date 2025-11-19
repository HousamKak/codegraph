# Edge Rendering Improvements

## Issues Fixed

### 1. Multiple Edges Overlapping
**Problem:** When there are multiple edges between the same pair of nodes, they were rendering on top of each other, making it impossible to see them individually.

**Solution:** Implemented curved paths using quadratic Bezier curves. Each parallel edge gets a different curve offset, spreading them in an arc.

**Technical Details:**
- Calculate link indices for each pair of nodes
- Apply perpendicular offset based on link index
- Use SVG quadratic Bezier path: `M(source) Q(control) (target)`
- Max curve offset: 80 pixels, distributed evenly

### 2. Edge Labels Not Aligned
**Problem:** Edge labels were horizontal, not following the edge direction. This made them hard to read and looked unprofessional.

**Solution:** Rotate edge labels to align with edge direction using SVG transforms.

**Technical Details:**
- Calculate angle using `Math.atan2(dy, dx)`
- Convert to degrees
- Flip text if upside down (angle > 90° or < -90°)
- Apply rotation transform at edge midpoint
- For curved edges, adjust label position along the curve

## Implementation

### Edge Path Rendering
```typescript
link.select('path')
  .attr('d', (d: any) => {
    const dx = d.target.x - d.source.x;
    const dy = d.target.y - d.source.y;
    const dr = Math.sqrt(dx * dx + dy * dy);

    const linkIndex = d.linkIndex || 0;
    const linkCount = d.linkCount || 1;
    let curve = 0;

    if (linkCount > 1) {
      const maxCurve = 80;
      const step = maxCurve / (linkCount - 1);
      curve = (linkIndex * step) - (maxCurve / 2);
    }

    if (curve === 0) {
      return `M${d.source.x},${d.source.y}L${d.target.x},${d.target.y}`;
    } else {
      const mx = (d.source.x + d.target.x) / 2;
      const my = (d.source.y + d.target.y) / 2;
      const offsetX = -dy / dr * curve;
      const offsetY = dx / dr * curve;
      return `M${d.source.x},${d.source.y}Q${mx + offsetX},${my + offsetY} ${d.target.x},${d.target.y}`;
    }
  });
```

### Label Rotation
```typescript
link.select('text')
  .attr('transform', (d: any) => {
    const dx = d.target.x - d.source.x;
    const dy = d.target.y - d.source.y;
    const dr = Math.sqrt(dx * dx + dy * dy);

    // Calculate curve position
    const linkIndex = d.linkIndex || 0;
    const linkCount = d.linkCount || 1;
    let curve = 0;

    if (linkCount > 1) {
      const maxCurve = 80;
      const step = maxCurve / (linkCount - 1);
      curve = (linkIndex * step) - (maxCurve / 2);
    }

    // Position at midpoint (adjusted for curve)
    let mx = (d.source.x + d.target.x) / 2;
    let my = (d.source.y + d.target.y) / 2;

    if (curve !== 0) {
      const offsetX = -dy / dr * curve * 0.5;
      const offsetY = dx / dr * curve * 0.5;
      mx += offsetX;
      my += offsetY;
    }

    // Calculate rotation angle
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;

    // Keep text upright
    if (angle > 90 || angle < -90) {
      angle += 180;
    }

    return `translate(${mx},${my}) rotate(${angle})`;
  });
```

## Visual Result

### Before
```
A ━━━━━━━━━ B
  (All edges overlapping, horizontal labels)
```

### After
```
A ╭─CALLS──╮ B
  │         │
  ├─USES───┤
  │         │
  ╰─IMPORTS╯
  (Curved edges, rotated labels along edge)
```

## Files Modified

1. **frontend/src/components/GraphView.tsx**
   - Added link index calculation (lines 109-128)
   - Changed from `<line>` to `<path>` (line 151)
   - Updated tick function with curved paths (lines 253-285)
   - Updated tick function with rotated labels (lines 288-326)

2. **frontend/src/components/DiffView.tsx**
   - Added link index calculation (lines 122-138)
   - Changed from `<line>` to `<path>` (line 158)
   - Updated tick function with curved paths (lines 260-285)
   - Updated tick function with rotated labels (lines 288-320)

## Testing

The frontend should now display:
- ✅ Multiple edges between same nodes as separate curves
- ✅ Edge labels rotated to match edge direction
- ✅ Labels positioned along curved edges
- ✅ Labels never upside down

## Browser Compatibility

Uses standard SVG features:
- Quadratic Bezier paths (Q command)
- SVG transforms (translate, rotate)
- Compatible with all modern browsers

## Performance

- O(E) preprocessing to calculate link indices (E = number of edges)
- O(E) per frame to update paths and labels
- Negligible performance impact for graphs < 1000 edges
