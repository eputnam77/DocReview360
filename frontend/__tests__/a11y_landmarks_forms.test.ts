/**
 * Accessibility — Tasks 6, 8, 9
 *
 * Task 8 — Landmarks and heading structure:
 *   - Every public/authenticated page has a meaningful <h1>.
 *   - Search form uses role="search" landmark.
 *
 * Task 9 — Form and error announcement improvements:
 *   - Login page has an aria-live assertive region for errors.
 *   - Login inputs use aria-describedby + aria-invalid when errors occur.
 *   - Profile form: all Label elements have htmlFor pointing to a matching input id.
 *   - Profile form: select elements have id attributes matching their Labels.
 *   - Search input has an associated <label htmlFor> for its accessible name.
 *
 * Task 6 — Custom interactive widget keyboard parity:
 *   - Plugin marketplace toggle buttons have aria-pressed attribute.
 *   - Plugin marketplace toggle buttons have aria-label attribute.
 *   - Icon-only toggle buttons mark decorative icons with aria-hidden.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

// ---------------------------------------------------------------------------
// Task 8 — Landmarks: login page h1
// ---------------------------------------------------------------------------

describe("login.tsx — landmark h1 (Task 8)", () => {
  const login = src("pages/login.tsx");

  it("has a <h1> element for the page title", () => {
    expect(login).toMatch(/<h1\b/);
  });

  it("h1 is sr-only so it does not duplicate the CardTitle visual heading", () => {
    expect(login).toContain('className="sr-only"');
  });

  it("CardTitle is aria-hidden to prevent duplicate announcement", () => {
    expect(login).toContain('aria-hidden="true"');
  });
});

// ---------------------------------------------------------------------------
// Task 8 — Landmarks: search page h1 and form role
// ---------------------------------------------------------------------------

describe("search.tsx — landmark h1 and search role (Task 8)", () => {
  const search = src("pages/search.tsx");

  it("has a <h1> page heading", () => {
    expect(search).toMatch(/<h1\b/);
  });

  it("form has role='search' landmark", () => {
    expect(search).toContain('role="search"');
  });

  it("search input has an id for label association", () => {
    expect(search).toContain('id="search-input"');
  });

  it("search input label has htmlFor matching the input id", () => {
    expect(search).toContain('htmlFor="search-input"');
  });
});

// ---------------------------------------------------------------------------
// Task 9 — Form errors: login aria-live and aria-describedby
// ---------------------------------------------------------------------------

describe("login.tsx — error announcements (Task 9)", () => {
  const login = src("pages/login.tsx");

  it("has a persistent aria-live assertive region", () => {
    expect(login).toContain('aria-live="assertive"');
  });

  it("aria-live region has role='alert' for immediate announcement", () => {
    expect(login).toContain('role="alert"');
  });

  it("aria-live region has aria-atomic='true' for full re-read on update", () => {
    expect(login).toContain('aria-atomic="true"');
  });

  it("aria-live region has id='login-error' for aria-describedby reference", () => {
    expect(login).toContain('id="login-error"');
  });

  it("username input uses aria-describedby when there is an error", () => {
    expect(login).toContain('aria-describedby={loginError ? "login-error" : undefined}');
  });

  it("password input uses aria-describedby when there is an error", () => {
    // Both inputs share the same pattern — verify it appears twice
    const matches = login.match(/aria-describedby=\{loginError \? "login-error" : undefined\}/g);
    expect(matches).not.toBeNull();
    expect(matches!.length).toBeGreaterThanOrEqual(2);
  });

  it("username input marks itself aria-invalid when there is an error", () => {
    expect(login).toContain("aria-invalid={loginError ? true : undefined}");
  });

  it("sets loginError state when login fails", () => {
    expect(login).toContain("setLoginError(msg)");
  });

  it("clears loginError at the start of each login attempt", () => {
    expect(login).toContain('setLoginError("")');
  });
});

// ---------------------------------------------------------------------------
// Task 9 — Form labels: profile form id/htmlFor associations
// ---------------------------------------------------------------------------

describe("profile.tsx — label/input associations (Task 9)", () => {
  const profile = src("pages/profile.tsx");

  const pairs: [string, string][] = [
    ['htmlFor="profile-picture-url"', 'id="profile-picture-url"'],
    ['htmlFor="profile-picture-file"', 'id="profile-picture-file"'],
    ['htmlFor="profile-display-name"', 'id="profile-display-name"'],
    ['htmlFor="profile-email"', 'id="profile-email"'],
    ['htmlFor="profile-phone"', 'id="profile-phone"'],
    ['htmlFor="profile-shorthand"', 'id="profile-shorthand"'],
    ['htmlFor="profile-job-title"', 'id="profile-job-title"'],
    ['htmlFor="profile-department"', 'id="profile-department"'],
    ['htmlFor="profile-timezone"', 'id="profile-timezone"'],
    ['htmlFor="profile-theme"', 'id="profile-theme"'],
    ['htmlFor="profile-new-password"', 'id="profile-new-password"'],
    ['htmlFor="profile-confirm-password"', 'id="profile-confirm-password"'],
  ];

  for (const [labelFor, inputId] of pairs) {
    it(`Label with ${labelFor} has a matching input with ${inputId}`, () => {
      expect(profile).toContain(labelFor);
      expect(profile).toContain(inputId);
    });
  }

  it("confirm-password label is sr-only to avoid visual duplication", () => {
    expect(profile).toContain('htmlFor="profile-confirm-password"');
    expect(profile).toContain("sr-only");
  });
});

// ---------------------------------------------------------------------------
// Task 6 — Custom widget keyboard parity: plugin marketplace toggles
// ---------------------------------------------------------------------------

describe("plugin-marketplace.tsx — toggle button ARIA (Task 6)", () => {
  const marketplace = src("pages/configuration/plugin-marketplace.tsx");

  it("toggle buttons have aria-pressed attribute", () => {
    expect(marketplace).toContain("aria-pressed={plugin.isEnabled");
  });

  it("toggle buttons have a descriptive aria-label", () => {
    expect(marketplace).toContain("aria-label={`${plugin.isEnabled");
  });

  it("aria-label communicates current state (Enable/Disable)", () => {
    expect(marketplace).toContain("'Disable'");
    expect(marketplace).toContain("'Enable'");
  });

  it("decorative toggle icons have aria-hidden='true'", () => {
    expect(marketplace).toContain('aria-hidden="true"');
  });

  it("status text uses aria-live='polite' to announce toggle changes", () => {
    expect(marketplace).toContain('aria-live="polite"');
  });
});
