---
name: "UniStudy AI Design System"
version: "1.0.0"
description: "Design tokens, visual identity guidelines, and component specifications for UniStudy AI."

colors:
  primary:
    DEFAULT: "#4f46e5"       # Indigo 600 - Main action & branding
    hover: "#4338ca"         # Indigo 700
    active: "#3730a3"        # Indigo 800
    light: "#eef2ff"         # Indigo 50
    border: "#c7d2fe"        # Indigo 200
  secondary:
    DEFAULT: "#0284c7"       # Sky 600 - Complementary information
    light: "#f0f9ff"         # Sky 50
    border: "#bae6fd"        # Sky 200
  evidence:
    DEFAULT: "#059669"       # Emerald 600 - Verified syllabus evidence
    light: "#ecfdf5"         # Emerald 50
    border: "#a7f3d0"        # Emerald 200
    badge: "#065f46"         # Emerald 800 - High contrast text
  surface:
    canvas: "#f8fafc"        # Slate 50 - Global app background
    card: "#ffffff"          # Pure white - Content cards
    sidebar: "#ffffff"       # Pure white - Sidebar
    subtle: "#f1f5f9"        # Slate 100 - Secondary containers & hover
    modal: "#0f172a"         # Slate 900 - PDF viewer canvas
  neutral:
    text: "#0f172a"          # Slate 900 - Primary text (WCAG AAA)
    muted: "#64748b"         # Slate 500 - Secondary text & labels
    subtle: "#94a3b8"        # Slate 400 - Timestamps & captions
    border: "#e2e8f0"        # Slate 200 - Card & separator borders
    border-subtle: "#f1f5f9" # Slate 100 - Divider lines
  feedback:
    danger: "#dc2626"        # Red 600
    danger-light: "#fef2f2"  # Red 50
    danger-border: "#fecaca" # Red 200
    warning: "#d97706"       # Amber 600
    warning-light: "#fffbeb" # Amber 50
    warning-border: "#fde68a"# Amber 200
    success: "#16a34a"       # Green 600
    success-light: "#f0fdf4" # Green 50

typography:
  fontFamily:
    sans: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    mono: "'JetBrains Mono', 'Fira Code', ui-monospace, monospace"
  fontSize:
    "2xs": "0.6875rem"       # 11px - Micro labels, metadata
    xs: "0.75rem"            # 12px - Badges, captions
    sm: "0.875rem"           # 14px - Body text, inputs, buttons
    base: "1rem"             # 16px - Prominent titles, main lead
    lg: "1.125rem"           # 18px - Section headers
    xl: "1.25rem"            # 20px - Page titles
    "2xl": "1.5rem"          # 24px - Hero titles

spacing:
  0: "0px"
  0.5: "2px"
  1: "4px"
  1.5: "6px"
  2: "8px"
  2.5: "10px"
  3: "12px"
  4: "16px"
  5: "20px"
  6: "24px"
  8: "32px"
  10: "40px"
  12: "48px"

rounded:
  sm: "6px"
  md: "8px"
  lg: "12px"
  xl: "16px"
  "2xl": "20px"
  "3xl": "24px"
  full: "9999px"

shadows:
  xs: "0 1px 2px 0 rgb(0 0 0 / 0.04)"
  sm: "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)"
  md: "0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.08)"
  lg: "0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.08)"
  xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)"
---

# UniStudy AI Design System Specification

## 1. Design Philosophy: Academic Clarity & High Density
UniStudy AI is an academic companion designed for university students and educators. The interface balances:
- **Calm, Distraction-Free Focus:** Clean whites, soft neutral surfaces, and intentional indigo accents prioritize reading comprehension and study efficiency.
- **Evidence-First Visual Hierarchy:** Citations and syllabus references are treated as first-class UI elements with emerald validation indicators, unambiguous page badges, and immediate access to original sources.
- **Immediate Interactivity:** Instant feedback states, inline document rendering without cumbersome downloads, and accessible keyboard navigation.

---

## 2. Color System & Contrast
- **Primary Brand (`#4f46e5` - Indigo):** Reserved for primary actions, active navigation items, and user chat bubbles. Gives an authoritative yet welcoming academic presence.
- **Evidence Emerald (`#059669` - Emerald):** Used strictly for verified course citations, matching scores, and grounded answers.
- **Neutral Canvas (`#f8fafc` - Slate 50):** The app backdrop provides subtle contrast against white content cards (`#ffffff`).
- **Contrast Guarantee:** Primary text (`#0f172a`) on white achieves a **15.8:1 contrast ratio**, far exceeding WCAG AAA requirements (7:1).

---

## 3. Component Design Specifications

### 3.1 Chat Messages
- **Assistant Message:**
  - Background: Pure White (`#ffffff`), border: `slate-200/90`, shadow: `shadow-xs`.
  - Icon: Indigo rounded badge (`w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200/60`).
  - Text: `text-sm leading-relaxed text-slate-800`.
  - Sources block: Separated with a subtle divider, clear header with citation count.
- **User Message:**
  - Background: Indigo 600 (`#4f46e5`), text: white.
  - Border radius: `rounded-2xl rounded-tr-xs` for asymmetric conversational flow.

### 3.2 Evidence & Source Cards
- Card container: `border border-slate-200 rounded-xl bg-white hover:border-indigo-300 transition-colors`.
- Header:
  - Numerical index pill: `w-5 h-5 rounded-md bg-indigo-100 text-indigo-700 font-semibold text-[10px]`.
  - Document title: Truncated with full tooltip.
  - Page badge: `Trang PDF {page}` with `bg-indigo-50 text-indigo-700 border border-indigo-200/60`.
  - Cosine match score: Subtle mono text (`text-[10px] text-slate-400 font-mono`).
- Primary action:
  - Button "Xem toàn bộ PDF (Trang {page})": Solid indigo button with book icon.
  - Button "Mở tab mới": Secondary subtle button with external link icon.

### 3.3 Interactive In-App PDF Reader
- Modal Backdrop: `bg-slate-900/80 backdrop-blur-xs`.
- Header Toolbar:
  - Document title with icon.
  - Page navigator: `Trang [ X ] / [ Total ]` with `<` and `>` buttons.
  - View mode toggle: Segmented pill `Cuộn tất cả trang` vs `Từng trang`.
  - Zoom controls: `-`, `100%`, `+`, `Fit width`.
  - Action buttons: `Mở tab mới`, `Tải về`, `Đóng (Esc)`.
- Page Canvas:
  - Dark room canvas (`bg-slate-950`).
  - Individual pages styled with white background, subtle border, and elevation shadow.
  - Highlight ring around the cited page.

### 3.4 Sidebar & Navigation
- Modern floating layout or crisp border-right (`border-slate-200/80`).
- New conversation CTA: Prominent styled button with `bg-indigo-50 hover:bg-indigo-100 text-indigo-700`.
- Course selector: Clean dropdown with course status indicators (green dot for ready, amber for empty).
- Document list: File icon, document name, page count badge.
- Upload dropzone: Dashed border with hover transition and clear file size guidelines.

---

## 4. Do's and Don'ts

### Do:
- Always use semantic design tokens and Tailwind utility classes defined in the system.
- Ensure all interactive elements have visible focus states (`focus-visible:ring-2 focus-visible:ring-indigo-500`).
- Display verified syllabus sources prominently with page numbers and confidence indicators.
- Provide clear loading skeletons and empty states with helpful guidance prompts.

### Don't:
- Never hardcode arbitrary hex colors (e.g. `#1a2b3c`) in JSX/TSX components.
- Never use automatic browser downloads for document viewing; always use the in-app interactive reader.
- Never compromise on text contrast; ensure text is easily readable under all lighting conditions.
- Don't use inconsistent border radii; adhere to the 8px (md), 12px (lg), 16px (xl) scale.
