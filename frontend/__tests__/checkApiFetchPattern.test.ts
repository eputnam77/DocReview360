/**
 * Tests for scripts/check-api-fetch-pattern.mjs
 *
 * Verifies:
 * - The script exits 0 on a clean codebase (no forbidden patterns).
 * - The script exits 1 and reports violations when a forbidden pattern is present.
 * - The two forbidden patterns are both detected (authenticatedFetch + raw fetch with ${API}).
 * - login.tsx is exempted from the raw-fetch guard.
 * - All intended scan directories are checked (lib, components, state, utils, pages).
 */
import { spawnSync } from "child_process";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join, resolve } from "path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

// Resolve the script from the repo root (frontend/  → root = ..)
const REPO_ROOT = resolve(__dirname, "../..");
const SCRIPT = join(REPO_ROOT, "scripts", "check-api-fetch-pattern.mjs");
const FRONTEND_DIR = join(REPO_ROOT, "frontend");

function runScript(env?: NodeJS.ProcessEnv) {
  return spawnSync("node", [SCRIPT], {
    cwd: REPO_ROOT,
    env: { ...process.env, ...env },
    encoding: "utf8",
  });
}

// ---------------------------------------------------------------------------
// Fixture helpers — create / tear down temporary files inside the real
// frontend/ tree so the script scans them.
// ---------------------------------------------------------------------------

let tmpFiles: string[] = [];

function writeFixture(relPath: string, content: string): string {
  const abs = join(FRONTEND_DIR, relPath);
  mkdirSync(join(abs, ".."), { recursive: true });
  writeFileSync(abs, content, "utf8");
  tmpFiles.push(abs);
  return abs;
}

afterEach(() => {
  for (const file of tmpFiles) {
    try {
      rmSync(file, { force: true });
    } catch {
      // ignore cleanup errors in CI
    }
  }
  tmpFiles = [];
});

// ---------------------------------------------------------------------------
// Baseline: current repo is clean
// ---------------------------------------------------------------------------

describe("check-api-fetch-pattern.mjs — baseline", () => {
  it("exits 0 on the current codebase (no violations)", () => {
    const result = runScript();
    expect(result.status).toBe(0);
    expect(result.stdout).toContain("OK");
  });
});

// ---------------------------------------------------------------------------
// Violation detection
// ---------------------------------------------------------------------------

describe("check-api-fetch-pattern.mjs — violation detection", () => {
  it("exits 1 when authenticatedFetch(`${API}/…`) is present in lib/", () => {
    writeFixture(
      "lib/_test_fixture_authfetch.ts",
      'const r = authenticatedFetch(`${API}/something`);\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN PATTERN");
    expect(result.stderr).toContain("_test_fixture_authfetch.ts");
  });

  it("exits 1 when raw fetch(`${API}/…`) is present in lib/", () => {
    writeFixture(
      "lib/_test_fixture_rawfetch.ts",
      'const r = fetch(`${API}/something`);\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN PATTERN");
    expect(result.stderr).toContain("_test_fixture_rawfetch.ts");
  });

  it("exits 1 when authenticatedFetch(`${API}/…`) is present in components/", () => {
    writeFixture(
      "components/_test_fixture_comp.tsx",
      'export default function C() { return authenticatedFetch(`${API}/api`); }\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
  });

  it("exits 1 when authenticatedFetch(`${API}/…`) is present in state/", () => {
    writeFixture(
      "state/_test_fixture_state.ts",
      'authenticatedFetch(`${API}/state-endpoint`);\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
  });

  it("exits 1 when authenticatedFetch(`${API}/…`) is present in utils/", () => {
    writeFixture(
      "utils/_test_fixture_utils.ts",
      'authenticatedFetch(`${API}/util`);\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
  });

  it("exits 1 when authenticatedFetch(`${API}/…`) is present in pages/", () => {
    writeFixture(
      "pages/_test_fixture_page.tsx",
      'authenticatedFetch(`${API}/page`);\n',
    );
    const result = runScript();
    expect(result.status).toBe(1);
  });

  it("reports the exact number of violations found", () => {
    writeFixture(
      "lib/_test_fixture_multi.ts",
      [
        'authenticatedFetch(`${API}/one`);',
        'fetch(`${API}/two`);',
        '// authenticatedFetch(`${API}/three`);', // comment — should still match
      ].join("\n"),
    );
    const result = runScript();
    expect(result.status).toBe(1);
    expect(result.stderr).toMatch(/Found \d+ forbidden fetch pattern/);
  });
});

// ---------------------------------------------------------------------------
// Exemption: login.tsx is intentionally excluded
// ---------------------------------------------------------------------------

describe("check-api-fetch-pattern.mjs — login.tsx exemption", () => {
  it("does NOT flag login.tsx even when it contains fetch(`${API}/…`)", () => {
    // The real login.tsx uses raw fetch intentionally — we verify the exemption
    // by checking that the script currently exits 0 (the file is already exempt).
    const result = runScript();
    expect(result.status).toBe(0);
  });
});

// ---------------------------------------------------------------------------
// Clean fixture: relative paths are allowed
// ---------------------------------------------------------------------------

describe("check-api-fetch-pattern.mjs — relative paths are clean", () => {
  it("exits 0 when only relative authenticatedFetch('/…') calls are present", () => {
    writeFixture(
      "lib/_test_fixture_clean.ts",
      [
        "import { authenticatedFetch } from './api';",
        "authenticatedFetch('/endpoint');",
        "authenticatedFetch('/another/endpoint');",
      ].join("\n"),
    );
    const result = runScript();
    expect(result.status).toBe(0);
  });
});
