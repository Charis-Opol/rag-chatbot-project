---
name: Institutional Excellence
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
  secondary: '#575e72'
  on-secondary: '#ffffff'
  secondary-container: '#dbe2fa'
  on-secondary-container: '#5d6478'
  tertiary: '#002416'
  on-tertiary: '#ffffff'
  tertiary-container: '#003c28'
  on-tertiary-container: '#36b080'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d4e3ff'
  primary-fixed-dim: '#a6c8ff'
  on-primary-fixed: '#001c3b'
  on-primary-fixed-variant: '#204778'
  secondary-fixed: '#dbe2fa'
  secondary-fixed-dim: '#bfc6dd'
  on-secondary-fixed: '#141b2c'
  on-secondary-fixed-variant: '#3f4759'
  tertiary-fixed: '#85f8c4'
  tertiary-fixed-dim: '#68dba9'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 12px
  md: 24px
  lg: 48px
  xl: 80px
  container-max: 1280px
  gutter: 24px
---

## Brand & Style

This design system embodies the authority and reliability of a modern government institution while adopting a premium, high-utility aesthetic. The brand personality is professional, transparent, and efficient, moving away from legacy bureaucratic clutter toward a "clean-enterprise" philosophy.

The style is rooted in **Modern Corporate Minimalism**. It prioritizes extreme legibility, generous negative space, and a refined structural hierarchy. By utilizing high-quality typography and a disciplined layout, the UI evokes a sense of calm confidence and accessibility, ensuring citizens and administrators alike feel a sense of trust and clarity.

## Colors

The palette is anchored by the primary **Brand Blue (#023464)**, used purposefully for navigation, primary actions, and institutional markers. To achieve depth without visual noise, the system introduces a sophisticated scale of neutrals.

- **Surface:** The base page background is absolute white (#FFFFFF) to maximize contrast.
- **Surface-Container-Low:** #F8FAFC (Slate 50) for subtle background differentiation.
- **Surface-Container-Medium:** #F1F5F9 (Slate 100) for UI headers or secondary sectioning.
- **Surface-Container-High:** #E2E8F0 (Slate 200) for subtle borders and hairline dividers.
- **Interactive:** Use the primary blue for high-priority buttons. Use a soft secondary blue (#E0E7FF) for low-emphasis interactions.

## Typography

The design system utilizes **Inter** for all typography to ensure a systematic and utilitarian feel that remains highly readable across all resolutions. 

Tighten letter-spacing on larger display types to maintain a "premium" feel, while increasing line heights on body text to promote scanning and reduce cognitive load. Labels use all-caps with increased tracking for clear categorization in data-heavy views.

## Layout & Spacing

The system follows a **12-column fixed-width grid** for desktop, centering content within a 1280px container to prevent excessive line lengths on ultra-wide monitors. 

**Spacing Rhythm:**
- **Vertical Breathing:** Use `xl` (80px) spacing between major sections to emphasize clarity and premium quality.
- **Component Padding:** Internal padding for cards and sections should never fall below `md` (24px).
- **Mobile Adaptivity:** At 768px, the grid transitions to a fluid model with 16px margins and 16px gutters, reducing padding to `sm` (12px) for compact efficiency.

## Elevation & Depth

This design system uses a **Tonal & Shadow Hybrid** approach to signify hierarchy without relying on heavy colors.

- **Hairline Strokes:** Use 1px borders in `Surface-Container-High` (#E2E8F0) for all cards and input fields. This provides structure without the "weight" of traditional borders.
- **Ambient Elevation:** Primary floating elements (like modals or dropdowns) use a high-diffusion, low-opacity shadow: `0 12px 32px rgba(2, 52, 100, 0.08)`. The slight blue tint in the shadow ties the elevation back to the brand identity.
- **Flat Containers:** Standard dashboard panels are flat with a `Surface-Container-Low` background to create a tiered visual stack against the white base.

## Shapes

The design system employs a **Soft** shape language. A consistent 0.25rem (4px) radius is applied to standard UI elements like inputs and buttons to maintain a professional, institutional character. Larger containers and cards use 0.5rem (8px) to soften the interface slightly, ensuring it feels modern and approachable rather than rigid.

## Components

**Buttons**
- **Primary:** Brand Blue background, white text, 4px radius. High horizontal padding (24px) for a premium feel.
- **Secondary:** Surface-Container-Medium background with no border. For low-priority actions.

**Input Fields**
- Use hairline borders (#E2E8F0) and a subtle 4px corner radius. Focused states utilize a 2px Brand Blue ring with high offset to ensure accessibility and clarity.

**Cards**
- Cards are the primary organizational unit. They should be borderless with the Ambient Elevation shadow, or use a hairline stroke if placed on a colored surface. Content within cards must adhere to the 24px internal margin rule.

**Data Tables**
- Rows should have a height of at least 56px to ensure "breathing room." Use hairline horizontal dividers only; avoid vertical lines to maintain a cleaner, more modern look.

**Breadcrumbs & Status Chips**
- Use `label-md` typography. Status chips for government workflows (e.g., "Pending," "Approved") use high-legibility, low-saturation background tints with high-contrast text.