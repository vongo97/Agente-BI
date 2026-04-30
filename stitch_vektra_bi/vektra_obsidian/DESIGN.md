# Design System Document: High-End Intelligence Editorial

## 1. Overview & Creative North Star
**The Creative North Star: "The Luminous Architect"**

The design system for this platform moves beyond the "SaaS Dashboard" trope. It is a high-end editorial experience that treats complex data as a gallery piece. Instead of rigid boxes and heavy lines, we use **Tonal Layering** and **Atmospheric Depth** to guide the user. 

The aesthetic is defined by "The Luminous Architect"—a philosophy where the interface feels like a physical architectural model carved from midnight glass and illuminated by internal light. We break the template look through **intentional asymmetry**: metrics are not always perfectly centered; they are balanced by generous negative space. Large typography scales create a sense of authority, while glassmorphism adds a layer of sophisticated mystery appropriate for cutting-edge AI.

---

### 2. Colors & Surface Philosophy
The palette is rooted in a deep, nocturnal base, utilizing a spectrum of blue-toned darks to create depth without relying on antiquated borders.

#### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or containment. Boundaries must be defined solely through background color shifts.
*   **Correct:** A `surface-container-low` card sitting on a `surface` background.
*   **Incorrect:** A card with a grey border to separate it from the background.

#### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the surface-container tiers to create "nested" depth:
*   **Base Layer (`surface` / `#0b1326`):** The canvas.
*   **Section Layer (`surface-container-low` / `#131b2e`):** Large groupings or sidebar backgrounds.
*   **Component Layer (`surface-container` / `#171f33`):** Primary cards and data containers.
*   **Highlight Layer (`surface-container-high` / `#222a3d`):** Hover states or active selections.

#### The "Glass & Gradient" Rule
To signify AI-driven insights, use **Glassmorphism**. Floating elements (Modals, Popovers, Tooltips) should use semi-transparent surface colors with a `backdrop-blur` of 12px–20px. 
*   **Signature Textures:** Apply a subtle linear gradient to main CTAs (from `primary` to `primary_container`) with a 15% opacity `secondary` (Neon Violet) glow to provide "visual soul."

---

### 3. Typography
We use **Inter** as a precision tool. The hierarchy is designed to make data feel like a headline, not just a number.

*   **Display (lg/md/sm):** Used for hero metrics and AI-generated insights. These should feel monumental. (e.g., `display-lg`: 3.5rem).
*   **Headline (lg/md/sm):** Used for page titles and major section headers. High contrast against the background is key.
*   **Title (lg/md/sm):** For card headings and widget titles.
*   **Body (lg/md/sm):** Optimized for legibility. Use `on_surface_variant` (#c2c6d6) for secondary body text to reduce visual fatigue.
*   **Labels (md/sm):** All-caps or tracking-heavy styles for technical metadata and small UI elements.

**Metric Legibility:** When displaying data, always use the `font-feature-settings: 'tnum' on, 'lnum' on;` CSS property to ensure tabular (monospaced) numbers, preventing layout shift during live data updates.

---

### 4. Elevation & Depth
In this design system, light is the primary architect of hierarchy.

*   **The Layering Principle:** Depth is achieved by "stacking" surface-container tiers. Place a `surface-container-lowest` card on a `surface-container-low` section to create a soft, natural "recessed" effect.
*   **Ambient Shadows:** For floating components, use an extra-diffused shadow.
    *   *Spec:* `box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);`
    *   *Color:* The shadow should be a tinted version of the background, never pure black.
*   **The "Ghost Border" Fallback:** If accessibility requires a border (e.g., in high-contrast needs), use a "Ghost Border": `outline-variant` (#424754) at **15% opacity**.
*   **Glassmorphism Depth:** Elements using `surface_variant` at 60% opacity with a blur create an "overlay" feel that integrates the background colors into the foreground.

---

### 5. Components

#### Buttons
*   **Primary:** `primary` background with `on_primary` text. Use `xl` (1.5rem) roundedness. Hover state: A subtle `primary` outer glow (`box-shadow: 0 0 20px rgba(173, 198, 255, 0.3)`).
*   **Secondary:** `surface-container-highest` background. Subtle and integrated.
*   **Tertiary:** No background. Text-only with `primary` color.

#### Input Fields
*   **Container:** `surface-container-low` with a 12px (`md`) radius. 
*   **State:** On focus, the background shifts to `surface-container` and a "Ghost Border" illuminates at 40% opacity using the `primary` color.

#### Cards & Lists
*   **Forbid Divider Lines.** Separate list items using `spacing-4` (1rem) of vertical white space or a subtle background toggle between `surface-container` and `surface-container-low`.
*   **Interactive Cards:** On hover, cards should lift slightly via a transition to `surface-container-highest` and a +2px Y-axis shift.

#### Specialized AI Insights (The "Aura" Component)
*   For AI-driven suggestions, use a container with a `secondary` (Neon Violet) inner glow and a 10% `secondary_container` background. This distinguishes human-fed data from machine-generated intelligence.

---

### 6. Do’s and Don’ts

#### Do
*   **Do** use asymmetrical margins (e.g., 64px on the left, 80px on the right) to create an editorial, non-generic layout.
*   **Do** prioritize "Breathing Room." If a section feels crowded, increase the spacing scale by one tier (e.g., move from `8` to `10`).
*   **Do** use `tertiary` (Emerald Green) and `error` (Amber/Red) sparingly for high-signal alerts only.

#### Don't
*   **Don't** use 100% white (#FFFFFF) for body text. It causes "halation" in dark mode. Use `on_surface` (#dae2fd).
*   **Don't** use standard "drop shadows" with 0 blur. Shadows must feel like ambient light.
*   **Don't** use lines to separate data. If the data isn't separated enough, the typography hierarchy or background contrast is failing.
*   **Don't** use sharp corners. Everything must adhere to the `lg` (1rem) or `xl` (1.5rem) roundedness scale to maintain the "Soft Minimalism" feel.

---

### 7. Technical Implementation (Tailwind Reference)