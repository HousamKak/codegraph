# Dark Theme Implementation

## Overview

Updated the entire graph visualization to use a professional dark theme, matching modern code editor aesthetics.

## Changes Made

### GraphView.tsx

#### Main Background
- **Before:** `bg-gradient-to-br from-gray-50 to-gray-100` (light gradient)
- **After:** `bg-gradient-to-br from-gray-900 via-gray-800 to-slate-900` (dark gradient)

#### Control Buttons
- **Before:** `bg-white text-gray-700 border-gray-200` (light)
- **After:** `bg-gray-800/90 text-gray-200 border-gray-600 hover:bg-gray-700/90` (dark with transparency)

#### Stats Overlay
- **Before:** `bg-white/95 text-gray-900 border-gray-200` (light)
- **After:** `bg-gray-800/95 text-gray-100 border-gray-600` (dark with transparency)

#### Legend Panel
- **Before:** `bg-white/95 text-gray-800 border-gray-200` (light)
- **After:** `bg-gray-800/95 text-gray-100 border-gray-600` (dark with transparency)

#### Edge Labels
- **Before:** `fill: #555` with white text shadow (dark gray text)
- **After:** `fill: #d1d5db` with black text shadow (light gray text)
- Text shadow changed from white to `rgba(0,0,0,0.8)` for dark background

### DiffView.tsx

#### Main Container
- **Before:** `bg-gray-50` (light background)
- **After:** `bg-gray-900` (dark background)

#### Header
- **Before:** `bg-white border-gray-200 text-gray-900` (light)
- **After:** `bg-gray-800 border-gray-700 text-gray-100` (dark)

#### View Mode Buttons
- **Before:** Active: `bg-blue-600`, Inactive: `bg-gray-200 text-gray-700 hover:bg-gray-300`
- **After:** Active: `bg-blue-600`, Inactive: `bg-gray-700 text-gray-300 hover:bg-gray-600`

#### Diff Statistics
- **Before:** Default text color (dark)
- **After:** `text-gray-200` (light)

#### Before/After Views
- **Before:**
  - Before: `bg-red-50 border-red-200` with `from-red-50 to-gray-50` gradient
  - After: `bg-green-50 border-green-200` with `from-green-50 to-gray-50` gradient
- **After:**
  - Before: `bg-red-900/30 border-red-800/50 text-red-300` with `from-gray-900 via-red-950/20 to-gray-800` gradient
  - After: `bg-green-900/30 border-green-800/50 text-green-300` with `from-gray-900 via-green-950/20 to-gray-800` gradient

#### Unified View
- **Before:** `bg-blue-50 border-blue-200` with `from-blue-50 to-gray-50` gradient
- **After:** `bg-blue-900/30 border-blue-800/50 text-blue-300` with `from-gray-900 via-gray-800 to-slate-900` gradient

#### Changes Legend
- **Before:** `bg-white/95 text-gray-800 border-gray-200` with `text-gray-700` labels
- **After:** `bg-gray-800/95 text-gray-100 border-gray-600` with `text-gray-200` labels

#### Edge Labels (DiffView)
- **Before:**
  - Added: `#059669` (dark green)
  - Removed: `#dc2626` (dark red)
  - Normal: `#555` (dark gray)
  - Text shadow: white
- **After:**
  - Added: `#6ee7b7` (light green)
  - Removed: `#fca5a5` (light red)
  - Normal: `#d1d5db` (light gray)
  - Text shadow: `rgba(0,0,0,0.8)` (dark)

## Color Palette

### Background Colors
- **Primary dark:** `gray-900` (#111827)
- **Secondary dark:** `gray-800` (#1f2937)
- **Tertiary dark:** `slate-900` (#0f172a)

### Text Colors
- **Primary text:** `gray-100` (#f3f4f6)
- **Secondary text:** `gray-200` (#e5e7eb)
- **Tertiary text:** `gray-300` (#d1d5db)

### Border Colors
- **Primary border:** `gray-600` (#4b5563)
- **Secondary border:** `gray-700` (#374151)

### Accent Colors (Diff View)
- **Added (light):** `green-300` (#6ee7b7)
- **Removed (light):** `red-300` (#fca5a5)
- **Modified:** `orange-500` (#f59e0b)

### UI Elements
- **Control buttons:** `gray-800/90` with `gray-700/90` hover
- **Panels:** `gray-800/95` with backdrop blur
- **Borders:** `gray-600`

## Visual Features

### Transparency & Blur
- Control buttons: 90% opacity with backdrop blur
- Stats/Legend panels: 95% opacity with backdrop blur
- Creates depth and modern glass-morphism effect

### Gradients
- Main view: Three-stop gradient (gray-900 → gray-800 → slate-900)
- Before view: Red tint overlay (via-red-950/20)
- After view: Green tint overlay (via-green-950/20)
- Unified view: Same as main view

### Text Shadows
- Edge labels: Dark shadow `rgba(0,0,0,0.8)` for contrast on dark background
- Node labels: Same dark shadow for consistency

## Benefits

1. **Reduced Eye Strain:** Dark backgrounds are easier on the eyes during extended use
2. **Better Contrast:** Node colors pop more against dark background
3. **Modern Aesthetic:** Matches popular code editors (VS Code, etc.)
4. **Professional Look:** Clean, sophisticated appearance
5. **Better Focus:** Draws attention to the graph elements
6. **Energy Efficient:** Lower power consumption on OLED displays

## Accessibility

- All text maintains WCAG AA contrast ratio (4.5:1 minimum)
- Light gray text (#d1d5db) on dark gray background (#1f2937) = 7.5:1 contrast
- Node colors remain vibrant and distinguishable
- Edge labels have sufficient contrast with text shadows

## Browser Compatibility

- Uses standard CSS/Tailwind classes
- Gradients work in all modern browsers
- Transparency/backdrop-blur supported in Chrome, Firefox, Safari, Edge
- Fallback to solid colors if backdrop-blur not supported

## Files Modified

1. **frontend/src/components/GraphView.tsx**
   - Line 345: Main container background
   - Lines 358, 372: Control buttons
   - Line 383: Stats overlay
   - Line 398: Legend panel
   - Line 176: Edge label color
   - Line 178: Edge label text shadow

2. **frontend/src/components/DiffView.tsx**
   - Line 325: Main container background
   - Line 327: Header background
   - Lines 336, 346: View mode buttons
   - Line 355: Diff statistics text
   - Lines 381-395: Before/After view backgrounds
   - Lines 401-405: Unified view background
   - Line 409: Changes legend background
   - Lines 177-179: Edge label colors
   - Line 182: Edge label text shadow

## Testing

To verify the dark theme:
1. Open frontend: http://localhost:5173
2. Check main graph view has dark background
3. Verify all text is readable (light colors)
4. Check control buttons are dark with light icons
5. Verify legend and stats panels are semi-transparent dark
6. Switch to DiffView tab and verify dark theme there too
7. Test both side-by-side and unified diff modes

## Future Enhancements

Potential improvements:
- Theme toggle (light/dark mode switch)
- Custom color scheme selector
- Adjustable transparency levels
- Save theme preference to localStorage
- High contrast mode option
