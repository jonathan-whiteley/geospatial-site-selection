# Little Caesars Site Selection App - Design Specification

## Project Overview
A site selection dashboard for analyzing Little Caesars store locations, competitors, coverage areas, and simulated new store scenarios with interactive map visualization.

---

## Visual Design System

### Brand Colors
```css
Primary Orange: #F06B38
Primary Black: #000000
White: #FFFFFF

UI Colors:
- Background: #F0F4F8
- Border Gray: #E0E7EF
- Text Gray Dark: #374151
- Text Gray Medium: #6B7280
- Text Gray Light: #9CA3AF

Map Colors:
- Mall Stores: #3B82F6 (Blue)
- Street Stores: #10B981 (Green)
- Hypermarket Stores: #8B5CF6 (Purple)
- Competitors: #F59E0B (Amber)
- Coverage Areas: #10B981 with 10% opacity
```

### Typography
- **Font Family**: System font stack (sans-serif)
- **Header (h1)**: 24px, medium weight
- **Subheader (h2)**: 20px, medium weight
- **Body**: 16px, normal weight
- **Small Text**: 14px
- **Tiny Text**: 12px

### Spacing Scale
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px

### Border Radius
- Small: 8px
- Medium: 10px
- Large: 12px
- Full: 50% (circles)

---

## Application Layout

### Overall Structure
```
┌─────────────────────────────────────────────────────────────┐
│ Header (Orange #F06B38)                                     │
│ - Logo (left)                                               │
│ - Title: "Site Selection Dashboard"                        │
│ - Nav: "Explore" | "My Analysis" (right)                   │
├──────────┬─────────────────────────────────┬────────────────┤
│          │                                 │                │
│ Sidebar  │         Map View                │ Detail Panel   │
│ (320px)  │         (flex-1)                │ (384px)        │
│          │                                 │ (conditional)  │
│ Layers & │    Interactive Canvas Map       │                │
│ Controls │    - Stores (circles)           │ Store Details  │
│          │    - Competitors (diamonds)     │ - Sales Data   │
│          │    - Coverage Areas             │ - Analysis     │
│          │    - Zoom/Pan Controls          │ - Actions      │
│          │    - Legend                     │                │
│          │                                 │                │
└──────────┴─────────────────────────────────┴────────────────┘
```

---

## Component Specifications

## 1. Header Component

**Height**: 64px  
**Background**: #F06B38  
**Layout**: Flexbox, space-between

### Elements:
```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Site Selection Dashboard         Explore | My Analysis │
└─────────────────────────────────────────────────────────────┘
```

**Left Side**:
- Little Caesars Logo (height: 48px, margin-right: 16px)
- Title text: "Site Selection Dashboard" (white, 20px)

**Right Side**:
- Navigation buttons (white text, hover: opacity 80%)
- Gap between buttons: 24px

---

## 2. Sidebar Component

**Width**: 320px  
**Background**: White  
**Border Right**: 1px solid #E0E7EF  
**Padding**: 16px  
**Overflow**: Auto scroll

### Layer Control Pattern (Repeating):
```
┌──────────────────────────────────────┐
│ [▼] Layer Name           [Toggle ON] │
│                                      │
│     → Expanded Content               │
│       - Sub-options                  │
│       - Filters                      │
│       - Range sliders                │
└──────────────────────────────────────┘
```

### Layers List:
1. **Covered Areas**
   - Toggle switch (right)
   - Collapsible (chevron icon)
   - No sub-options

2. **Stores** (Expanded by default)
   - Toggle switch
   - Collapsible
   - Sub-section: "By store location"
     - Legend items:
       - Blue dot + "MALL"
       - Green dot + "STREET"  
       - Purple dot + "HYPERMARKET"
   - Sub-section: "RADIUS RANGE BY"
     - Label: "average revenue"
     - Two range sliders:
       - MAX slider (top, value displayed above)
       - MIN slider (bottom, value displayed below)
     - Range: 65,560 to 1,032,435
     - Accent color: #F06B38

3. **Simulated Stores**
   - Toggle switch
   - Collapsible (collapsed by default)

4. **Population**
   - Toggle switch
   - Collapsible (collapsed by default)

5. **Competitors**
   - Toggle switch
   - Collapsible
   - No sub-options

### Footer:
- Border top: 1px solid #E0E7EF
- "Layers" button with icon

---

## 3. Map View Component

**Background**: #F0F4F8  
**Rendering**: HTML5 Canvas  
**Interactions**: Click, drag to pan, zoom controls

### Visual Elements:

#### Grid Background
- Light gray grid: #E0E7EF
- Grid size: 50px (scales with zoom)

#### Streets (Mock)
- Color: #C5D1DE
- Width: 2px
- 3-4 intersecting street lines

#### Coverage Areas (if enabled)
- Polygon shape with dashed border
- Fill: rgba(16, 185, 129, 0.1)
- Stroke: #10B981, 2px, dashed (5px dash, 5px gap)
- Circular radius overlay: 80px * zoom

#### Store Markers (if enabled and in revenue range)
- **Shape**: Circle
- **Size**: 20px diameter
- **Border**: 2px white
- **Shadow**: 2px offset, rgba(0,0,0,0.2)
- **Colors by type**:
  - Mall: #3B82F6
  - Street: #10B981
  - Hypermarket: #8B5CF6
- **Hover state**: Orange (#F06B38) outline, 3px, 3px offset
- **Click**: Opens detail panel

#### Competitor Markers (if enabled)
- **Shape**: Diamond (rotated square)
- **Size**: 24px
- **Color**: #F59E0B
- **Border**: 2px white
- **Shadow**: 2px offset
- **Rotation**: 45 degrees

#### Labels
- Area names: Gray text (#6B7280), 14px
- Position: Above points of interest

### Controls Overlay (Bottom Right)

**Position**: Absolute, bottom: 24px, right: 24px  
**Stack**: Vertical, gap: 8px

Three buttons:
1. **Home** (center map) - Home icon
2. **Zoom In** - Plus icon
3. **Zoom Out** - Minus icon

Button style:
- Background: White
- Padding: 12px
- Border radius: 8px
- Shadow: 0 4px 6px rgba(0,0,0,0.1)
- Border: 1px solid #E5E7EB
- Hover: Background #F9FAFB
- Icon: 20px, color #374151

### Legend Overlay (Top Right)

**Position**: Absolute, top: 24px, right: 24px  
**Background**: White  
**Padding**: 16px  
**Border radius**: 8px  
**Shadow**: 0 4px 6px rgba(0,0,0,0.1)

Content:
- Title: "Map Legend" (14px)
- Margin bottom: 12px
- Legend items (12px text, 8px gap):
  - Blue circle + "Mall Stores"
  - Green circle + "Street Stores"
  - Purple circle + "Hypermarket"
  - Amber rotated square + "Competitors"

### Attribution (Bottom Left)
**Position**: Absolute, bottom: 8px, left: 8px  
**Background**: rgba(255,255,255,0.9)  
**Padding**: 4px 8px  
**Border radius**: 4px  
**Text**: "© Little Caesars Site Selection" (12px, gray)

### Hover Tooltip
**Trigger**: Mouse over store marker  
**Position**: Follow cursor (+15px x, -40px y)  
**Style**:
- Background: White
- Padding: 8px 12px
- Border radius: 8px
- Shadow: 0 4px 12px rgba(0,0,0,0.15)
- Pointer events: none (no interaction)

**Content**:
```
Store #5
Mall
Revenue: $850K
```

---

## 4. Detail Panel Component

**Width**: 384px  
**Background**: White  
**Border Left**: 1px solid #E0E7EF  
**Shadow**: Large shadow for depth  
**Overflow**: Auto scroll  
**Animation**: Slide in from right

### Header (Sticky)
**Background**: White  
**Border bottom**: 1px solid #E0E7EF  
**Padding**: 16px

```
┌────────────────────────────────┐
│ SIMULATED STORE                │
│ Store Demo #5              [X] │
└────────────────────────────────┘
```

- Small label: "SIMULATED STORE" (12px, gray, uppercase)
- Store name: "Store Demo #5" (20px, #F06B38)
- Close button: X icon, top right, 20px

### Store ID Section
**Padding**: 16px  
**Border bottom**: 1px solid #E0E7EF

- Icon + ID (map pin icon, 16px, gray)
- Monospace font for ID
- Button: "Compare simulations"
  - Full width
  - Background: #F06B38
  - Text: White
  - Padding: 8px 16px
  - Border radius: 8px
  - Icon: BarChart3 (16px)
  - Hover: Darken to #d85f30

### Quick Stats Section
**Padding**: 16px  
**Border bottom**: 1px solid #E0E7EF

- Icon row: 4 icons (Car, Users, Store, MapPin), gray, 20px
- Gap: 12px
- Info card:
  - Background: #F9FAFB
  - Border radius: 8px
  - Padding: 12px
  - Text: "Area by driving time"
  - Value: "10 min" (18px)

### Analysis Section
**Padding**: 16px

**Section Title**: "Analysis" (12px, gray, uppercase, tracking wide)

#### 1. Sales Prediction
- Icon + Label: TrendingUp icon + "Sales prediction"
- Value: Large text (24px) "$XXK - $XXK"
- Progress bar:
  - Height: 8px
  - Background: #E5E7EB
  - Fill: Gradient from #F06B38 to #F59E0B
  - Border radius: full
  - Width: 75%

#### 2. Cannibalization
- Icon + Label: BarChart3 + "Stores cannibalized"
- List of 3 items:
  ```
  Downtown Store          31%
  West End Store          24%
  Eastside Store          18%
  ```
  - Flexbox: space-between
  - Text: 14px
  - Gap: 12px between rows

#### 3. Store Details Card
- Background: #F9FAFB
- Border radius: 8px
- Padding: 16px
- Gap: 8px
- Rows:
  ```
  Store Type:         Mall
  Current Revenue:    $850K
  Location:           40.7589, -73.9851
  ```
  - Label: Gray (#6B7280)
  - Value: Black
  - Font: 14px

### Action Buttons
**Margin top**: 24px  
**Layout**: Flex row, gap: 8px

1. **Primary Action** (flex: 1)
   - Text: "Search twin areas"
   - Border: 1px solid #F06B38
   - Color: #F06B38
   - Background: Transparent
   - Hover: Background #F06B38, Text white
   - Padding: 8px 16px
   - Border radius: 8px

2. **Share Icon Button**
   - Border: 1px solid #D1D5DB
   - Padding: 8px
   - Icon: Share nodes (20px)
   - Hover: Background #F9FAFB

3. **Download Icon Button**
   - Border: 1px solid #D1D5DB
   - Padding: 8px
   - Icon: Download (20px)
   - Hover: Background #F9FAFB

---

## Data Structures

### Store Interface
```typescript
interface Store {
  id: number;
  type: 'mall' | 'street' | 'hypermarket';
  lat: number;
  lng: number;
  revenue: number;
}
```

### Competitor Interface
```typescript
interface Competitor {
  id: number;
  lat: number;
  lng: number;
  name: string;
}
```

### Mock Data

**Stores** (5 locations in NYC):
```javascript
[
  { id: 1, type: 'mall', lat: 40.7589, lng: -73.9851, revenue: 850000 },
  { id: 2, type: 'street', lat: 40.7489, lng: -73.9751, revenue: 720000 },
  { id: 3, type: 'hypermarket', lat: 40.7689, lng: -73.9651, revenue: 950000 },
  { id: 4, type: 'street', lat: 40.7389, lng: -73.9951, revenue: 680000 },
  { id: 5, type: 'mall', lat: 40.7789, lng: -73.9551, revenue: 920000 }
]
```

**Competitors** (4 locations):
```javascript
[
  { id: 1, lat: 40.7529, lng: -73.9801, name: "Domino's Pizza" },
  { id: 2, lat: 40.7629, lng: -73.9701, name: "Pizza Hut" },
  { id: 3, lat: 40.7429, lng: -73.9901, name: "Papa John's" },
  { id: 4, lat: 40.7729, lng: -73.9601, name: "Domino's Pizza" }
]
```

**Coverage Area Polygon**:
```javascript
[
  [40.7689, -73.9951],
  [40.7789, -73.9751],
  [40.7689, -73.9551],
  [40.7489, -73.9551],
  [40.7389, -73.9751],
  [40.7489, -73.9951]
]
```

---

## Interaction Patterns

### Toggle Switches
- **Default**: Gray background (#CBCED4)
- **Active**: Orange background (#F06B38)
- **Handle**: White circle, 16px
- **Track**: 40px × 20px, rounded full
- **Animation**: Smooth translate on handle

### Collapsible Sections
- **Closed**: ChevronRight icon (16px)
- **Open**: ChevronDown icon (16px)
- **Click area**: Entire header row
- **Animation**: Smooth expand/collapse

### Range Sliders
- **Track**: Gray background (#E5E7EB)
- **Thumb**: Accent color (#F06B38)
- **Labels**: Above/below slider
- **Min/Max**: 65,560 to 1,032,435
- **Display format**: Comma-separated numbers

### Map Interactions
- **Pan**: Click and drag canvas
- **Cursor**: Grab (default), Grabbing (dragging)
- **Zoom**: +/- buttons or scroll wheel
- **Zoom range**: 0.5x to 3x
- **Store click**: Open detail panel with animation
- **Hover**: Show tooltip, highlight marker

### Buttons
- **Primary**: Orange background, white text
- **Secondary**: Orange border, orange text, transparent background
- **Icon-only**: Gray border, gray icon
- **Hover**: Slight background change or opacity shift
- **Transition**: 200ms ease

---

## State Management

### Application State
```typescript
{
  // Layer toggles
  showCoveredAreas: boolean (default: true)
  showStores: boolean (default: true)
  showSimulatedStores: boolean (default: false)
  showPopulation: boolean (default: false)
  showCompetitors: boolean (default: true)
  
  // Filters
  revenueRange: [min: number, max: number] (default: [65560, 1032435])
  
  // Map state
  zoom: number (default: 1)
  pan: { x: number, y: number } (default: {x: 0, y: 0})
  
  // UI state
  selectedStore: Store | null
  isDetailPanelOpen: boolean (default: false)
  hoveredStore: Store | null
}
```

---

## Technical Requirements

### Framework
- **React** (functional components with hooks)
- **TypeScript** (for type safety)
- **Tailwind CSS** (for styling)

### Key Libraries
- **lucide-react** (icons)
- No external mapping libraries (custom canvas implementation)

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Canvas API required

### Performance
- Canvas rendering for map (better performance than DOM markers)
- Debounced pan/zoom updates
- Filter stores by revenue before rendering

### Responsive Considerations
- Desktop-first design
- Minimum width: 1280px recommended
- Sidebar collapsible on smaller screens (future enhancement)

---

## File Structure

```
/
├── App.tsx                    # Main application component
├── components/
│   ├── Sidebar.tsx           # Left sidebar with layer controls
│   ├── MapView.tsx           # Canvas-based map visualization
│   └── DetailPanel.tsx       # Right panel with store details
├── styles/
│   └── globals.css           # Global styles and CSS variables
└── assets/
    └── logo.png              # Little Caesars logo
```

---

## Assets Needed

### Logo
- **File**: Little Caesars logo (PNG with transparency)
- **Usage**: Header left side
- **Size**: Height 48px (maintain aspect ratio)
- **URL**: figma:asset/39448687bbf7f4e379417367f391027cfad63853.png

### Icons (from lucide-react)
- ChevronDown
- ChevronRight
- Layers
- Home
- Plus
- Minus
- X
- BarChart3
- MapPin
- TrendingUp
- Users
- Car
- Store (StoreIcon)

---

## Calculations & Algorithms

### Lat/Lng to Pixel Conversion
```javascript
const latLngToPixel = (lat, lng, width, height, zoom, pan) => {
  const centerLat = 40.7589;  // NYC center
  const centerLng = -73.9851;
  const scale = 50000 * zoom;
  
  const x = (lng - centerLng) * scale + width / 2 + pan.x;
  const y = -(lat - centerLat) * scale + height / 2 + pan.y;
  
  return { x, y };
}
```

### Sales Prediction Range
```javascript
const salesPrediction = {
  min: (store.revenue * 0.85) / 1000,  // 15% lower
  max: (store.revenue * 1.15) / 1000   // 15% higher
}
```

### Revenue Display Format
```javascript
// Display in thousands with K suffix
const displayRevenue = (revenue) => {
  return `$${(revenue / 1000).toFixed(0)}K`;
}
```

---

## Animation Specifications

### Panel Slide In
- **Trigger**: Store click
- **Duration**: 300ms
- **Easing**: ease-out
- **Transform**: translateX(384px) → translateX(0)

### Toggle Switch
- **Duration**: 200ms
- **Easing**: ease
- **Property**: background-color, transform

### Hover Effects
- **Duration**: 150ms
- **Easing**: ease
- **Properties**: opacity, background-color

### Collapsible Sections
- **Duration**: 200ms
- **Easing**: ease
- **Property**: height (auto-animate)

---

## Accessibility

### Keyboard Navigation
- Tab through interactive elements
- Enter/Space to activate buttons and toggles
- Escape to close detail panel

### ARIA Labels
- Toggle switches: aria-label describing layer
- Buttons: aria-label for icon-only buttons
- Map: aria-label="Interactive store location map"

### Color Contrast
- Text on white: minimum 4.5:1 ratio
- Orange buttons: white text for contrast
- Focus indicators: visible outline

---

## Future Enhancements (Not Implemented)

1. Search functionality
2. Export to PDF/Excel
3. Real-time collaboration
4. Mobile responsive design
5. Multiple simulation comparison view
6. Historical data timeline
7. Heat map overlays
8. Route planning
9. Custom polygon drawing
10. Integration with real mapping APIs (Google Maps, Mapbox)

---

## Build Instructions

### For AI Coding Tools:

1. **Initialize React + TypeScript project**
   ```bash
   npm create vite@latest site-selection-app -- --template react-ts
   cd site-selection-app
   npm install
   ```

2. **Install dependencies**
   ```bash
   npm install lucide-react
   npm install -D tailwindcss postcss autoprefixer
   npx tailwindcss init -p
   ```

3. **Configure Tailwind** (tailwind.config.js)
   ```javascript
   export default {
     content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
     theme: { extend: {} },
     plugins: [],
   }
   ```

4. **Create file structure** as specified above

5. **Copy component code** from design specification

6. **Add logo asset** to public folder

7. **Run dev server**
   ```bash
   npm run dev
   ```

### Key Implementation Notes:
- Use HTML5 Canvas for map rendering (not DOM elements)
- Implement click detection via coordinate math
- State management with React useState hooks
- CSS custom properties for theming
- Responsive canvas sizing with ResizeObserver

---

## Version History

- **v1.0** - Initial specification (January 2026)
  - Core map visualization
  - Layer controls
  - Detail panel
  - Little Caesars branding

---

**End of Specification Document**
