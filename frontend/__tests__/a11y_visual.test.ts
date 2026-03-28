/**
 * Accessibility — Tasks 11, 12, 13: Visual accessibility and robustness
 *
 * Task 11 — Contrast audit (light/dark themes):
 *   - CSS custom properties define foreground/background token pairs.
 *   - A dark mode variant exists (`.dark` selector in globals.css).
 *   - Muted foreground token is present (used for secondary text).
 *
 * Task 12 — Zoom / reflow / responsive checks:
 *   - Tailwind base styles are imported (responsive utilities available).
 *   - Body uses responsive bg/text tokens (not fixed pixel colors).
 *   - App shell uses flex/responsive layout utilities.
 *
 * Task 13 — Motion and target-size checks:
 *   - globals.css includes a `prefers-reduced-motion` media query.
 *   - The media query covers animation-duration (disables animations).
 *   - The media query covers transition-duration (disables transitions).
 *   - The media query covers scroll-behavior (prevents smooth-scroll jank).
 *   - Button component uses focus-visible ring (ensures visible focus target).
 *   - Button component uses disabled:opacity for sufficient target contrast.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

// ---------------------------------------------------------------------------
// Task 11 — Contrast audit: CSS token definitions
// ---------------------------------------------------------------------------

describe("styles/globals.css — contrast token definitions (Task 11)", () => {
  const css = src("styles/globals.css");

  it("defines --foreground token for primary text color", () => {
    expect(css).toContain("--foreground:");
  });

  it("defines --background token for page background", () => {
    expect(css).toContain("--background:");
  });

  it("defines --muted-foreground token for secondary/helper text", () => {
    expect(css).toContain("--muted-foreground:");
  });

  it("defines dark-mode override tokens in .dark selector", () => {
    expect(css).toContain(".dark {");
  });

  it(".dark redefines --foreground for light-on-dark contrast", () => {
    const darkBlock = css.slice(css.indexOf(".dark {"));
    expect(darkBlock).toContain("--foreground:");
  });

  it(".dark redefines --background for dark surface", () => {
    const darkBlock = css.slice(css.indexOf(".dark {"));
    expect(darkBlock).toContain("--background:");
  });
});

// ---------------------------------------------------------------------------
// Task 12 — Zoom / reflow: responsive base styles
// ---------------------------------------------------------------------------

describe("styles/globals.css — responsive / reflow baseline (Task 12)", () => {
  const css = src("styles/globals.css");

  it("imports Tailwind base layer (responsive utilities available)", () => {
    expect(css).toContain("@tailwind base");
  });

  it("imports Tailwind utilities layer (responsive class variants available)", () => {
    expect(css).toContain("@tailwind utilities");
  });

  it("body uses token-based text color (not hard-coded pixel value)", () => {
    expect(css).toContain("@apply bg-background text-foreground");
  });
});

describe("pages/_app.tsx — responsive layout (Task 12)", () => {
  const app = src("pages/_app.tsx");

  it("app shell uses flex layout for responsive sidebar + content arrangement", () => {
    expect(app).toMatch(/flex/);
  });

  it("main content region is identified by id for skip-link target", () => {
    expect(app).toContain('id="main-content"');
  });
});

// ---------------------------------------------------------------------------
// Task 13 — Motion: prefers-reduced-motion media query
// ---------------------------------------------------------------------------

describe("styles/globals.css — prefers-reduced-motion (Task 13)", () => {
  const css = src("styles/globals.css");

  it("includes a prefers-reduced-motion media query", () => {
    expect(css).toContain("prefers-reduced-motion");
  });

  it("reduces animation-duration to near zero for motion-sensitive users", () => {
    expect(css).toContain("animation-duration: 0.01ms");
  });

  it("reduces transition-duration to near zero", () => {
    expect(css).toContain("transition-duration: 0.01ms");
  });

  it("disables smooth scroll-behavior", () => {
    expect(css).toContain("scroll-behavior: auto");
  });

  it("limits animation-iteration-count to 1 to stop looping animations", () => {
    expect(css).toContain("animation-iteration-count: 1");
  });

  it("applies the rule to all elements via universal selector", () => {
    expect(css).toContain("*, *::before, *::after");
  });
});

// ---------------------------------------------------------------------------
// Task 13 — Target size: Button focus + interaction affordance
// ---------------------------------------------------------------------------

describe("components/ui/button.tsx — target size and focus (Task 13)", () => {
  const button = src("components/ui/button.tsx");

  it("uses focus-visible ring for keyboard focus indicator (WCAG 2.4.7)", () => {
    expect(button).toContain("focus-visible:");
  });

  it("sets type='button' by default to prevent accidental form submission", () => {
    expect(button).toContain('"button"');
  });

  it("applies reduced opacity on disabled state for visual affordance", () => {
    expect(button).toMatch(/disabled:[a-z-]*opacity/);
  });
});
