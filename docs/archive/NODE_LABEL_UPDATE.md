# Node Label Update

## Change Summary

### Before
- Node had abbreviated letter inside (F, C, M, V, P, etc.)
- Full name shown below the node (truncated if > 12 chars)
- Two separate text elements per node

### After
- Full node name shown inside the circle
- Name can overflow the circle boundary
- Color indicates node type (no abbreviation needed)
- Single text element per node

## Visual Comparison

**Before:**
```
   ┌─────┐
   │  F  │  ← Letter abbreviation
   └─────┘
  calculate_t...  ← Truncated name below
```

**After:**
```
   ┌──────────────┐
   │ calculate_total │  ← Full name inside (can overflow)
   └──────────────┘
```

## Color Key Remains

Node colors still indicate type:
- 🔵 **Blue** = Module
- 🟣 **Purple** = Class
- 🟢 **Green** = Function
- 🔷 **Teal** = Variable
- 🟡 **Yellow** = Parameter
- 🔴 **Red** = CallSite
- 🌸 **Pink** = Type
- 🟠 **Orange** = Decorator

## Implementation Details

### GraphView.tsx (lines 217-226)
```typescript
// Node labels (full name inside circle)
node.append('text')
  .text(d => d.label)
  .attr('text-anchor', 'middle')
  .attr('dy', '.35em')
  .attr('font-size', '10px')
  .attr('font-weight', 'bold')
  .attr('fill', 'white')
  .attr('pointer-events', 'none')
  .style('text-shadow', '0 1px 2px rgba(0,0,0,0.3)');
```

### DiffView.tsx (lines 232-241)
```typescript
// Node labels (full name inside circle)
node.append('text')
  .text((d: any) => d.label)
  .attr('text-anchor', 'middle')
  .attr('dy', '.35em')
  .attr('font-size', '10px')
  .attr('font-weight', 'bold')
  .attr('fill', 'white')
  .attr('pointer-events', 'none')
  .style('text-shadow', '0 1px 2px rgba(0,0,0,0.3)');
```

## Benefits

1. **Immediate Identification**: See the full function/class name at a glance
2. **No Truncation**: Long names are fully visible (overflow is fine)
3. **Cleaner Layout**: No label below the node
4. **Better Readability**: White text on colored background with shadow
5. **Consistent with Neo4j**: Similar to how Neo4j Browser shows node labels

## Technical Details

- Font size: 10px (readable but fits well)
- Font weight: bold (stands out)
- Color: white (contrasts with all node colors)
- Text shadow: `0 1px 2px rgba(0,0,0,0.3)` (improves readability)
- Vertical alignment: `.35em` (centers in circle)
- Text anchor: middle (horizontal centering)

## Files Modified

1. `frontend/src/components/GraphView.tsx`
   - Removed label below node (was at dy: 35)
   - Removed abbreviated type label
   - Added full name label inside circle

2. `frontend/src/components/DiffView.tsx`
   - Removed label below node (was at dy: 35)
   - Removed abbreviated type label
   - Added full name label inside circle

## Overflow Behavior

Long names will overflow the circle boundary, which is intentional:
- Allows full name visibility
- No truncation needed
- Still readable due to white text + shadow
- Similar to professional graph tools
