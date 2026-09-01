# RemitProof Design System

## Theme

Light, restrained product interface. The working scene is a finance controller reviewing exceptions in a bright office before posting receivables. The surface should feel like a precise digital ledger: calm enough for sustained use, structured enough for audit work, and visibly conservative around autonomous action.

## Color Palette

All interface colors use OKLCH.

- Canvas: `oklch(1 0 0)`
- Surface: `oklch(0.972 0.005 150)`
- Raised surface: `oklch(0.945 0.008 150)`
- Ink: `oklch(0.20 0.025 150)`
- Muted ink: `oklch(0.47 0.018 150)`
- Border: `oklch(0.875 0.009 150)`
- Primary: `oklch(0.40 0.106 150)`
- Primary dark: `oklch(0.30 0.085 150)`
- Accent: `oklch(0.42 0.12 255)`
- Success tint: `oklch(0.94 0.035 150)`
- Warning: `oklch(0.60 0.145 72)`
- Warning tint: `oklch(0.95 0.045 82)`
- Danger: `oklch(0.50 0.165 28)`
- Danger tint: `oklch(0.95 0.035 28)`

Strategy: restrained. Primary and semantic colors are reserved for decisions, focus, and current state. Inactive surfaces remain neutral.

## Typography

Use one system sans family for headings, controls, labels, and body text. Use fixed rem sizes with a compact product scale. Financial amounts, IDs, and rates use tabular numerals. Headings use balanced wrapping; explanatory prose stays below 70 characters per line.

## Components

- App header: quiet brand mark, product boundary, benchmark status.
- Decision badge: icon plus exact user-facing state; color never acts alone.
- Metric ledger: aligned labels and values, not a repeated card grid.
- Exception table: readable at operational density with a clear audit link.
- Proof checklist: explicit pass, fail, or not evaluated status for every deterministic check.
- Allocation ledger: invoice additions, credit deductions, and received total aligned on a numeric baseline.
- Evidence record: type, source ID, title, and inspectable content.
- Human-review callout: pale warning surface, direct reason, and useful next action context.

## Layout

Use a centered 1440px work area with 24px desktop gutters and 16px mobile gutters. Dashboard hierarchy flows from receipt pipeline, to safety outcome, to benchmark comparison, to recent exceptions. Detail hierarchy flows from payment and decision, to proof and evidence, to allocation and alternatives. At narrow widths, two-column regions stack and tables scroll horizontally.

## Motion

Use 150 to 200ms transitions for hover, focus, and state feedback only. No page-load choreography. Respect `prefers-reduced-motion` by removing transforms and reducing transition duration to near zero.

## Accessibility

Target WCAG 2.2 AA with strong body contrast, visible keyboard focus, semantic headings and tables, non-color decision cues, reduced-motion support, and layouts that remain usable at 200% zoom.
