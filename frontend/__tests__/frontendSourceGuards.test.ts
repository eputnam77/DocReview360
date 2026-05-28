import { spawnSync } from "child_process";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join, resolve } from "path";
import { afterEach, describe, expect, it } from "vitest";

const FRONTEND_DIR = resolve(__dirname, "..");
const RAW_FETCH_SCRIPT = join(FRONTEND_DIR, "scripts", "check-raw-fetch.mjs");
const NO_API_PROXY_SCRIPT = join(FRONTEND_DIR, "scripts", "check-no-api-proxy.mjs");
const RAW_FETCH_SHELL = join(FRONTEND_DIR, "scripts", "check-raw-fetch.sh");
const NO_API_PROXY_SHELL = join(FRONTEND_DIR, "scripts", "check-no-api-proxy.sh");

let tmpFiles: string[] = [];
let tmpDirs: string[] = [];

function runScript(script: string, env?: NodeJS.ProcessEnv) {
  return spawnSync(process.execPath, [script], {
    cwd: FRONTEND_DIR,
    env: { ...process.env, ...env },
    encoding: "utf8",
  });
}

function writeFixture(relPath: string, content: string) {
  const abs = join(FRONTEND_DIR, relPath);
  mkdirSync(join(abs, ".."), { recursive: true });
  writeFileSync(abs, content, "utf8");
  tmpFiles.push(abs);
  return abs;
}

function makeTempFrontendRoot() {
  const root = mkdtempSync(join(tmpdir(), "docreview360-source-guard-"));
  tmpDirs.push(root);
  return root;
}

function writeTempFixture(root: string, relPath: string, content: string) {
  const abs = join(root, relPath);
  mkdirSync(join(abs, ".."), { recursive: true });
  writeFileSync(abs, content, "utf8");
  return abs;
}

afterEach(() => {
  for (const file of tmpFiles) {
    rmSync(file, { force: true });
  }
  tmpFiles = [];
  for (const dir of tmpDirs) {
    rmSync(dir, { force: true, recursive: true });
  }
  tmpDirs = [];
});

describe("frontend source guard scripts", () => {
  it("pass on a clean source tree", () => {
    const root = makeTempFrontendRoot();
    writeTempFixture(root, "pages/clean.tsx", "export const value = 1;\n");
    writeTempFixture(root, "components/Clean.tsx", "export const value = 1;\n");

    expect(runScript(RAW_FETCH_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: root }).status).toBe(0);
    expect(runScript(NO_API_PROXY_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: root }).status).toBe(0);
  });

  it("flags raw fetch('/api/...') calls in pages", () => {
    const root = makeTempFrontendRoot();
    writeTempFixture(
      root,
      "pages/_test_fixture_raw_fetch.tsx",
      "export const load = () => fetch('/" + "api/projects');\n",
    );

    const result = runScript(RAW_FETCH_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: root });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN RAW FETCH");
    expect(result.stderr).toContain("_test_fixture_raw_fetch.tsx");
  });

  it("flags legacy apiProxy imports anywhere in frontend TypeScript", () => {
    const root = makeTempFrontendRoot();
    writeTempFixture(
      root,
      "components/_test_fixture_api_proxy.tsx",
      "import legacy from '../lib/" + "apiProxy';\n",
    );

    const result = runScript(NO_API_PROXY_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: root });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN API PROXY IMPORT");
    expect(result.stderr).toContain("_test_fixture_api_proxy.tsx");
  });

  it("fails loudly when a scan root cannot be read", () => {
    const missingRoot = join(FRONTEND_DIR, ".missing-source-root");

    const rawFetch = runScript(RAW_FETCH_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: missingRoot });
    const noApiProxy = runScript(NO_API_PROXY_SCRIPT, { DOCREVIEW360_FRONTEND_DIR: missingRoot });

    expect(rawFetch.status).toBe(2);
    expect(rawFetch.stderr).toContain("CHECK_RAW_FETCH_SCAN_FAILED");
    expect(noApiProxy.status).toBe(2);
    expect(noApiProxy.stderr).toContain("CHECK_NO_API_PROXY_SCAN_FAILED");
  });

  it("keeps legacy shell wrappers delegated to the loud Node scanners", () => {
    const rawFetchShell = readFileSync(RAW_FETCH_SHELL, "utf8");
    const noApiProxyShell = readFileSync(NO_API_PROXY_SHELL, "utf8");

    expect(rawFetchShell).not.toContain("|| true");
    expect(noApiProxyShell).not.toContain("|| true");
    expect(rawFetchShell).toContain('exec node "${SCRIPT_DIR}/check-raw-fetch.mjs"');
    expect(noApiProxyShell).toContain('exec node "${SCRIPT_DIR}/check-no-api-proxy.mjs"');
  });
});
