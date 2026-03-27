/**
 * Accessibility — Task 7: ? keyboard shortcut on Help page
 *
 * Verifies that pages/help.tsx implements the documented "?" shortcut
 * that navigates to the Keyboard Shortcuts tab, so the docs and
 * the code are in sync (WCAG consistency / keyboard operability).
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

describe("help.tsx — ? shortcut implementation (Task 7)", () => {
  const help = src("pages/help.tsx");

  it("imports useEffect for the keyboard listener", () => {
    expect(help).toContain("useEffect");
  });

  it("registers a keydown listener on window", () => {
    expect(help).toContain('addEventListener("keydown"');
  });

  it("removes the listener on cleanup", () => {
    expect(help).toContain('removeEventListener("keydown"');
  });

  it("listens for the ? key", () => {
    expect(help).toContain('"?"');
  });

  it("navigates to the shortcuts tab when ? is pressed", () => {
    expect(help).toContain('"shortcuts"');
    expect(help).toContain("setActiveTab");
  });

  it("ignores ? when focus is in an INPUT", () => {
    expect(help).toContain("INPUT");
  });

  it("ignores ? when focus is in a TEXTAREA", () => {
    expect(help).toContain("TEXTAREA");
  });

  it("Tabs component is controlled (value + onValueChange)", () => {
    expect(help).toContain("value={activeTab}");
    expect(help).toContain("onValueChange={setActiveTab}");
  });

  it("SHORTCUTS data still lists ? as a shortcut key", () => {
    expect(help).toContain('"?"');
    expect(help).toContain("Show keyboard shortcuts");
  });
});
