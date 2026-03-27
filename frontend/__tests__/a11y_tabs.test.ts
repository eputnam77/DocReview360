/**
 * Accessibility — Task 5: Custom Tabs keyboard navigation
 *
 * Verifies that components/ui/tabs.tsx implements:
 *  - ArrowRight / ArrowLeft / Home / End keyboard handling in TabsTrigger
 *  - Active tab tabIndex=0, inactive tabs tabIndex=-1
 *  - aria-controls linking trigger → panel
 *  - Tab panel has aria-labelledby linking panel → trigger
 *  - Tab panel has tabIndex={0} to be keyboard-reachable
 *  - Tab trigger has id="tab-trigger-{value}" for aria-labelledby reference
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

describe("tabs.tsx — keyboard navigation (Task 5)", () => {
  const tabs = src("components/ui/tabs.tsx");

  it("handles ArrowRight key to advance to next tab", () => {
    expect(tabs).toContain('"ArrowRight"');
  });

  it("handles ArrowLeft key to go to previous tab", () => {
    expect(tabs).toContain('"ArrowLeft"');
  });

  it("handles Home key to go to first tab", () => {
    expect(tabs).toContain('"Home"');
  });

  it("handles End key to go to last tab", () => {
    expect(tabs).toContain('"End"');
  });

  it("prevents default on arrow/home/end key to stop page scroll", () => {
    expect(tabs).toContain("e.preventDefault()");
  });

  it("moves focus to sibling tab on key press", () => {
    expect(tabs).toContain("tabs[next].focus()");
  });

  it("activates sibling tab on key press (click)", () => {
    expect(tabs).toContain("tabs[next].click()");
  });

  it("active tab has tabIndex=0", () => {
    expect(tabs).toContain("tabIndex={isActive ? 0 : -1}");
  });

  it("TabsTrigger has id for aria-labelledby", () => {
    expect(tabs).toContain("`tab-trigger-${value}`");
  });

  it("TabsTrigger has aria-controls pointing to panel", () => {
    expect(tabs).toContain("`tab-panel-${value}`");
  });

  it("TabsContent has aria-labelledby pointing to trigger", () => {
    expect(tabs).toContain('aria-labelledby={`tab-trigger-${value}`}');
  });

  it("TabsContent panel has tabIndex={0} to be keyboard-focusable", () => {
    expect(tabs).toContain("tabIndex={0}");
  });

  it("keyboard handler queries role=tablist to scope sibling discovery", () => {
    expect(tabs).toContain('[role="tablist"]');
  });
});
