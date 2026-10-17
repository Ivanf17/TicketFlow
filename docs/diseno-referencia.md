---
name: Logistics Dispatch & Incident Command
colors:
  surface: '#f8f9ff'
  surface-dim: '#ccdbf3'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d5e3fc'
  on-surface: '#0d1c2e'
  on-surface-variant: '#444651'
  inverse-surface: '#233144'
  inverse-on-surface: '#eaf1ff'
  outline: '#757682'
  outline-variant: '#c5c5d3'
  surface-tint: '#4059aa'
  primary: '#00236f'
  on-primary: '#ffffff'
  primary-container: '#1e3a8a'
  on-primary-container: '#90a8ff'
  inverse-primary: '#b6c4ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#3e2400'
  on-tertiary: '#ffffff'
  tertiary-container: '#5c3800'
  on-tertiary-container: '#ef9900'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#00164e'
  on-primary-fixed-variant: '#264191'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0d1c2e'
  surface-variant: '#d5e3fc'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
  headline-xl-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  headline-lg:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  headline-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 0.75rem
  gutter-mobile: 0.5rem
  margin: 1.5rem
  margin-tablet: 1rem
  margin-mobile: 0.75rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1.25rem
  space-xl: 2rem
---

## Brand & Style
The design system establishes a focused, high-reliability corporate operations workspace engineered for logistics, supply chain routing, and mission-critical incident tracking. It serves fleet managers, support coordinators, warehouse leads, and tier-1 to tier-3 technicians who process hundreds of dispatches, routing exceptions, and transit tickets daily.

The visual style blends **Corporate / Modern** precision with quiet, data-dense utility:
- **Calm, High-Clarity Operations**: The interface reduces visual fatigue over prolonged shifts by using balanced, soft neutral backdrops (#F8FAFC, #F1F5F9) instead of stark blinding white across full views.
- **Architectural Utility**: Crisp lines, structured information density, predictable visual weight, and zero decorative noise.
- **Immediate State Legibility**: Status-driven interaction paradigms allow operators to evaluate SLAs, priority states, and ownership transfers at a single glance.

## Colors
The color architecture reinforces authority, precision, and rapid situational awareness:

### Brand & Core Accents
- **Primary (`#1E3A8A`)**: Deep Navy / Indigo. Deployed for top-level interactive anchors, primary CTAs, active navigation items, brand accents, and table header accents.
- **Secondary (`#0D9488`)**: Deep Teal. Applied to secondary positive actions, filter badges, automation indicators, and quick-routing triggers.
- **Tertiary (`#F59E0B`)**: Warm Amber. Anchors time-sensitive warnings, approaching SLA breaches, and "Pending" lifecycle indicators.
- **Neutral (`#475569`)**: Slate. Delivers crisp, legible text and structural containment without harsh pure black tones.

### Semantic Lifecycle & Operational Badges
- **Status - Pending**: Surface `#FEF3C7`, Border `#FDE68A`, Text `#B45309`, Dot Indicator `#F59E0B`.
- **Status - In Progress**: Surface `#EFF6FF`, Border `#BFDBFE`, Text `#1D4ED8`, Dot Indicator `#2563EB`.
- **Status - Resolved**: Surface `#ECFDF5`, Border `#A7F3D0`, Text `#047857`, Dot Indicator `#10B981`.
- **Status - Critical / Escalated**: Surface `#FEF2F2`, Border `#FECACA`, Text `#B91C1C`, Dot Indicator `#EF4444`.

### Canvas & Surface Hierarchy
- **App Canvas (`#F8FAFC`)**: Base viewport background behind all panels and dashboards.
- **Sidebar & Surface Recessed (`#F1F5F9`)**: Navigation rails, grouped module trays, and active drag regions.
- **Card & Data Surface (`#FFFFFF`)**: Tables, modal panels, ticket work items, and details panels.
- **Subtle Boundaries (`#E2E8F0`)**: Hairline borders defining modules and tabular rows.

## Typography
This design system standardizes on **Inter** across all typographical layers to optimize functional legibility within dense ticket grids, metadata sidebars, and analytical metric cards.

- **Tabular Numerals**: Apply `font-feature-settings: "tnum" 1` to ticket IDs, shipment counts, time-elapsed clocks, SLA count-downs, and currency fields.
- **Hierarchy Rules**: Page headings rely on weight (`600` and `700`) rather than oversized scale to preserve vertical density. Operational labels and status badges use `label-sm` or `label-md` with `letter-spacing: 0.02em` for uppercase abbreviations (e.g., `SLA`, `POD`, `VIN`, `ETA`).

## Layout & Spacing
The layout architecture centers around a responsive, 12-column modular fluid dashboard framework anchored by persistent navigation controls.

### Structural Frame
- **Sidebar Navigation**: Fixed left-hand layout unit. Expands to `260px` in standard state and collapses to `72px` in icon-only compact state. Transition timing uses `200ms cubic-bezier(0.4, 0, 0.2, 1)`.
- **Top Application Bar**: Fixed `64px` height spanning the viewport width offset by the sidebar. Features a live notification center with counter badge, breadcrumbs, search shortcut (`Cmd+K`), and a role-switcher dropdown.
- **Data Main Canvas**: Structured with an 8px base spatial grid. Compact metric summary cards span top registers (`col-span-3` on desktop, `col-span-6` on tablet, `col-span-12` on mobile). Ticket listings utilize full tabular span (`col-span-12`).

### Responsive Reflow Rules
- **Desktop (>= 1280px)**: 12-column layout, `1.5rem` margins, persistent left sidebar, split-pane ticket drawer preview (slide-in master-detail at `480px`).
- **Tablet (768px - 1279px)**: 8-column layout, sidebar auto-collapses to `72px` icon rail, detail drawers switch to full modal overlays.
- **Mobile (< 768px)**: 4-column layout, sidebar recedes behind an off-canvas drawer triggered by header hamburger, tables shift into vertical card list items with stacked state flags.

## Elevation & Depth
Depth in the system is handled through a combination of crisp container borders and soft, daylight ambient shadowing. Heavy drop shadows and high-opacity black casts are avoided to preserve corporate neatness.

### Elevation Levels
- **Level 0 (Flat Surface)**: Background canvas (`#F8FAFC`) and recessed controls (`#F1F5F9`). Uses no shadow; boundaries defined strictly by 1px solid `#E2E8F0`.
- **Level 1 (Card & Module Layer - `shadow-sm`)**: Primary interactive surfaces (ticket rows, summary widgets, forms).
  - Formula: `0 1px 2px 0 rgba(15, 23, 42, 0.05)`.
  - Border: 1px solid `#E2E8F0`.
- **Level 2 (Hovered & Active Work Units - `shadow-md`)**: Raised cards on drag/hover, active filter popovers.
  - Formula: `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`.
  - Border: 1px solid `#CBD5E1`.
- **Level 3 (Floating Overlays & Modals)**: Quick-view ticket drawers, role selectors, notification center dropdowns.
  - Formula: `0 10px 15px -3px rgba(15, 23, 42, 0.1), 0 4px 6px -4px rgba(15, 23, 42, 0.05)`.
  - Border: 1px solid `#CBD5E1`.

## Shapes
The design uses soft, refined corner geometry balancing contemporary aesthetics with corporate utility:

- **Base Radius (`0.375rem` / `6px`)**: Standard input fields, table selection boxes, dropdown triggers, and status badges.
- **Medium Radius (`0.5rem` / `8px`)**: Action buttons, compact cards, navigation items, tooltips, and notification popovers.
- **Large Radius (`0.75rem` / `12px`)**: Primary operational dashboard cards, modal views, slide-over detail drawers, and multi-step dispatch workflows.
- **Full Radius (`9999px`)**: User avatars, SLA progress pills, circular icon action buttons, and status indicator dots.

## Components

### Buttons
- **Primary**: Background `#1E3A8A`, text `#FFFFFF`, border none, height `38px`, padding `0 16px`, radius `8px`. Hover: `#1E40AF`. Active: `#172554`. Focus: outline `2px solid #3B82F6` with `2px` offset.
- **Secondary (Teal Accent)**: Background `#0D9488`, text `#FFFFFF`. Hover: `#0F766E`. Active: `#115E59`.
- **Outline / Neutral**: Background `#FFFFFF`, text `#334155`, border `1px solid #CBD5E1`. Hover: `#F8FAFC` and border `#94A3B8`.
- **Ghost (Icon Only)**: Background transparent, text `#64748B`. Hover: `#F1F5F9`, text `#1E293B`.

### Status Badges & Chips
- Embedded with a leading `6px` solid status circle.
- Height: `24px`, padding `2px 8px`, typography `label-sm`, radius `9999px`.
- **Pending**: Background `#FEF3C7`, text `#B45309`, border `1px solid #FDE68A`, dot `#F59E0B`.
- **In Progress**: Background `#EFF6FF`, text `#1D4ED8`, border `1px solid #BFDBFE`, dot `#2563EB`.
- **Resolved**: Background `#ECFDF5`, text `#047857`, border `1px solid #A7F3D0`, dot `#10B981`.

### Data Cards & Modules
- Background `#FFFFFF`, border `1px solid #E2E8F0`, radius `12px` (`rounded-xl`), shadow `shadow-sm`.
- Card Header: `16px 20px` padding, bottom border `1px solid #F1F5F9`, featuring title in `headline-sm` alongside action shortcuts or metrics.
- Card Body: `20px` inner padding.

### Input Fields & Search Trays
- Height: `38px`, padding `0 12px`, radius `6px`.
- Surface `#FFFFFF`, border `1px solid #CBD5E1`, text `#0F172A`, placeholder `#94A3B8`.
- Focus State: border `#1E3A8A`, box-shadow `0 0 0 1px #1E3A8A`.
- Compact Table Filter Variant: Height `32px`, font-size `12px`.

### Tables & Incident Rows
- Column Headers: Height `36px`, background `#F8FAFC`, typography `label-sm`, text `#64748B`, border-bottom `1px solid #E2E8F0`.
- Row Cells: Height `52px`, background `#FFFFFF`, typography `body-md`, border-bottom `1px solid #F1F5F9`.
- Row Hover State: Background `#F8FAFC`. Selected State: `#EFF6FF`.

### Checkboxes & Radios
- Box size `16px x 16px`, radius `4px` (checkbox) or `9999px` (radio).
- Inactive: Border `1.5px solid #CBD5E1`, background `#FFFFFF`.
- Checked: Border `#1E3A8A`, background `#1E3A8A`, icon white checkmark.

### Collapsible Navigation Rail
- Expanded width `260px`, collapsed `72px`. Background `#F8FAFC`, right border `1px solid #E2E8F0`.
- Nav Item: Height `40px`, margin `4px 12px`, radius `8px`, text `#475569`.
- Active Item: Background `#1E3A8A`, text `#FFFFFF`, left accent indicator or bold glyph color.

### Top App Bar & Role Selector
- Height `64px`, background `#FFFFFF`, bottom border `1px solid #E2E8F0`, padding `0 24px`.
- Notification Bell: `36px` icon target with a floating count badge (`#EF4444`, text white, `10px`, min-width `18px`, centered).
- Role Switcher: Bordered chip dropdown (`#F1F5F9`, border `1px solid #E2E8F0`, height `34px`, padding `0 10px`, radius `6px`) displaying active profile tier (e.g., "Supervisor de Flota", "Operador de Logística").