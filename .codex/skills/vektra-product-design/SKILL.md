---
name: vektra-product-design
description: Apply Vektra BI product design standards. Use when redesigning or implementing frontend UI, dashboard layouts, chat experience, settings, report builder, simulation screens, visual summaries, navigation, styling, colors, spacing, typography, component states, or when the user asks to improve the app style or make it look more professional.
---

# Vektra Product Design

Design Vektra as a serious BI workspace with an AI analyst, not as a marketing site or generic chatbot.

## Visual Direction

- Use a quiet, professional, high-trust interface: compact, clear, data-dense, and fast to scan.
- Prefer product layouts: sidebar, toolbar, panels, tables, charts, inspectors, and split views.
- Avoid landing-page composition, oversized heroes, decorative gradients, floating blobs, and marketing copy.
- Keep cards for repeated items, modals, and genuinely framed tools. Do not nest cards inside cards.
- Use 6-8px border radius unless matching an existing local component.
- Use subtle borders and restrained shadows. Let spacing and hierarchy do most of the work.

## Color System

- Base: white, near-white, cool gray, charcoal text.
- Primary: deep teal or restrained blue-green.
- Secondary accents: cyan, soft lime, or amber for states and data highlights.
- Avoid one-note palettes dominated by purple, dark slate/blue, beige/tan, or brown/orange.
- Use semantic colors for success, warning, danger, info, and selected states.

## Typography And Density

- Use compact headings inside panels; reserve large type for true top-level moments.
- Do not scale text with viewport width.
- Keep letter spacing at `0`.
- Ensure button/card text fits on mobile and desktop.
- Favor short labels. Do not add visible instructional text explaining obvious controls.

## Components

- Use `lucide-react` icons for buttons and tool actions.
- Use icon buttons with tooltips for common actions: save, download, refresh, delete, close, expand, collapse.
- Use segmented controls for modes, toggles for boolean settings, sliders/inputs for numeric settings, tabs for views, and menus for option sets.
- Build complete empty, loading, error, disabled, hover, focus, and selected states.
- Charts must have clear titles, units, legends, and readable container sizing.

## Screen Patterns

- Chat: professional analyst console, not casual messaging. Keep messages readable, with structured answer blocks and chart/result actions.
- Dashboard: dense grid with consistent chart chrome, filters, and visible data-source context.
- Settings: technical control panel with grouped fields, validation, and clear save states.
- Simulation: workflow surface with hypothesis, agents, debate, report, and status progression.
- Visual summary: focused generator workspace with preview, mode controls, and export actions.

## Verification

- After significant UI changes, run the app and inspect desktop and mobile widths.
- Check for overlapping text, clipped buttons, layout shift, blank charts, unreadable contrast, and console errors.
- Scan CSS/classes to ensure the page does not collapse into a single dominant hue.
