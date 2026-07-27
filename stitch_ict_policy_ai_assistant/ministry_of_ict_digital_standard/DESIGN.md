---
name: Ministry of ICT Digital Standard
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#43474f'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#737780'
  outline-variant: '#c3c6d0'
  surface-tint: '#3b5f92'
  primary: '#001f40'
  on-primary: '#ffffff'
  primary-container: '#023464'
  on-primary-container: '#7a9ed4'
  inverse-primary: '#a6c8ff'
  secondary: '#9d4300'
  on-secondary: '#ffffff'
  secondary-container: '#fd761a'
  on-secondary-container: '#5c2400'
  tertiary: '#002039'
  on-tertiary: '#ffffff'
  tertiary-container: '#00365b'
  on-tertiary-container: '#5ba1e4'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e3ff'
  primary-fixed-dim: '#a6c8ff'
  on-primary-fixed: '#001c3b'
  on-primary-fixed-variant: '#204778'
  secondary-fixed: '#ffdbca'
  secondary-fixed-dim: '#ffb690'
  on-secondary-fixed: '#341100'
  on-secondary-fixed-variant: '#783200'
  tertiary-fixed: '#d0e4ff'
  tertiary-fixed-dim: '#9bcbff'
  on-tertiary-fixed: '#001d34'
  on-tertiary-fixed-variant: '#004a79'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
  slate-dark: '#0F172A'
  surface-border: '#E2E8F0'
  success-green: '#10B981'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-xl:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 30px
    fontWeight: '600'
    lineHeight: 38px
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-xl:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '400'
    lineHeight: 30px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  page-margin-desktop: 32px
  page-margin-mobile: 16px
  gutter: 24px
  container-max-width: 1440px
  section-gap: 64px
---

## Brand & Style

The design system is engineered to represent the Ministry of ICT and National Guidance as a forward-thinking, authoritative, and citizen-centric enterprise. It balances the gravity of governmental responsibility with the agility of a 2026-era technology platform.

The aesthetic follows a **Corporate Modern** movement, heavily influenced by high-tier SaaS productivity tools. It prioritizes clarity, performance, and accessibility. The style is defined by extensive white space, precise typography, and a "function-first" hierarchy that eliminates visual noise to foster trust and focus.

**Key Brand Pillars:**
- **Institutional Authority:** Grounded in deep, stable blues that signify reliability.
- **Digital Innovation:** High-energy accents and fluid transitions that reflect Uganda’s technological progress.
- **Radical Clarity:** A layout philosophy that makes complex national data digestible and transparent.

## Colors

The color palette is anchored by **Ministry Blue**, a deep navy that provides the necessary weight for an enterprise government system. This is paired with **Ministry Orange**, used sparingly for high-impact calls to action and critical interactive elements.

- **Primary (Ministry Blue):** Used for headers, primary navigation, and core brand moments.
- **Secondary (Ministry Orange):** Reserved for primary buttons, progress indicators, and status highlights.
- **Background Strategy:** The interface utilizes `#F8FAFC` for the main canvas, creating a "cool" professional atmosphere that contrasts cleanly against pure white (`#FFFFFF`) surface cards.
- **Gradients:** Use soft, linear gradients for dashboard headers (e.g., from `#023464` to `#2563A8` at 135 degrees) to add depth without compromising readability.

## Typography

**Inter** is the exclusive typeface for this design system. Its geometric yet humanist characteristics provide the "technological" feel required for an ICT Ministry while maintaining the legibility expected of a public institution.

- **Scale:** A tight, mathematical typographic scale ensures hierarchy is immediate. Use `headline-xl` for dashboard titles and `body-md` for standard data entries.
- **Weight Strategy:** Use `600` (Semi-bold) for interactive elements and headers to maintain a strong presence against the light background. 
- **Readability:** Body text should always use a minimum line height of 1.5x the font size to ensure accessibility for all citizens.

## Layout & Spacing

The layout philosophy is based on a **12-column fluid grid** for desktop and a **4-column grid** for mobile. 

- **Breathable Layouts:** This design system mandates high internal padding. Components should never feel crowded. Use the `section-gap` (64px) to separate major content blocks.
- **Rhythm:** All spacing (margins, padding, gaps) must be multiples of 8px. 
- **Alignment:** Content is primarily left-aligned to mirror the "F-pattern" of scanning, with the exception of specific dashboard metrics which may be centered within their respective cards.

## Elevation & Depth

To achieve the modern "Enterprise" look, depth is conveyed through **Tonal Layering** supplemented by **Ambient Shadows**.

1.  **Level 0 (Canvas):** `#F8FAFC` - The base background.
2.  **Level 1 (Surfaces):** Pure `#FFFFFF` cards with a 1px border of `#E2E8F0`. This creates a crisp, architectural feel.
3.  **Level 2 (Interaction):** When hovered or active, cards receive a soft, diffused shadow: `0 10px 15px -3px rgba(2, 52, 100, 0.05)`. Note the slight blue tint in the shadow to maintain brand harmony.
4.  **Level 3 (Overlays):** Modals and dropdowns use a more pronounced shadow to separate them from the work surface, combined with a backdrop blur (glassmorphism) of 8px to maintain context.

## Shapes

The shape language is sophisticated and approachable. We utilize a "Rounded" (Level 2) baseline which scales up for larger containers to emphasize the modern, friendly nature of the technology.

- **Standard Elements:** Buttons and Input fields use a 0.5rem (8px) radius.
- **Enterprise Cards:** Container cards use `rounded-xl` (1.5rem / 24px) to create the signature "premium" look requested.
- **Visual Consistency:** All icons and illustrations should mirror this roundedness; avoid sharp corners in iconography.

## Components

### Buttons
Primary buttons use **Ministry Blue** with high-contrast white text. They feature a subtle inner-top highlight (1px white at 10% opacity) to give them a slightly tactile, premium feel. Secondary buttons use a transparent background with a 1px border of `#023464`.

### Cards
Cards are the core of the enterprise experience. They must have `rounded-xl` corners, a pure white background, and a subtle border. Headers within cards should be separated by a light horizontal rule.

### Input Fields
Inputs should be minimalist: a light gray background (`#F1F5F9`) that turns white on focus with a 2px **Ministry Blue** border. Use `label-md` for field labels, placed consistently above the input.

### Data Visualization
Charts should use a custom palette derived from the brand colors:
- **Primary Series:** Ministry Blue (`#023464`)
- **Secondary Series:** Light Blue (`#70B5F9`)
- **Accent Series:** Ministry Orange (`#F97316`)
Use thin lines (2px) for line charts and avoid heavy fills. Grid lines should be minimal (`#F1F5F9`).

### Icons
Use **thin-stroke (1.5pt)** icons. Icons should be monochrome (Ministry Blue) in navigation, only using color when indicating a specific state (e.g., a green check for success).