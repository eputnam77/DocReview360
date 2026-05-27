import { spawnSync } from "child_process";
import { mkdirSync, rmSync, writeFileSync } from "fs";
import { join, resolve } from "path";
import { afterEach, describe, expect, it } from "vitest";

const FRONTEND_DIR = resolve(__dirname, "..");
const RAW_FETCH_SCRIPT = join(FRONTEND_DIR, "scripts", "check-raw-fetch.mjs");
const NO_API_PROXY_SCRIPT = join(FRONTEND_DIR, "scripts", "check-no-api-proxy.mjs");

let tmpFiles: string[] = [];

function runScript(script: string) {
  return spawnSync(process.execPath, [script], {
    cwd: FRONTEND_DIR,
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

afterEach(() => {
  for (const file of tmpFiles) {
    rmSync(file, { force: true });
  }
  tmpFiles = [];
});

describe("frontend source guard scripts", () => {
  it("pass on the current source tree", () => {
    expect(runScript(RAW_FETCH_SCRIPT).status).toBe(0);
    expect(runScript(NO_API_PROXY_SCRIPT).status).toBe(0);
  });

  it("flags raw fetch('/api/...') calls in pages", () => {
    writeFixture(
      "pages/_test_fixture_raw_fetch.tsx",
      "export const load = () => fetch('/" + "api/projects');\n",
    );

    const result = runScript(RAW_FETCH_SCRIPT);
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN RAW FETCH");
    expect(result.stderr).toContain("_test_fixture_raw_fetch.tsx");
  });

  it("flags legacy apiProxy imports anywhere in frontend TypeScript", () => {
    writeFixture(
      "components/_test_fixture_api_proxy.tsx",
      "import legacy from '../lib/" + "apiProxy';\n",
    );

    const result = runScript(NO_API_PROXY_SCRIPT);
    expect(result.status).toBe(1);
    expect(result.stderr).toContain("FORBIDDEN API PROXY IMPORT");
    expect(result.stderr).toContain("_test_fixture_api_proxy.tsx");
  });
});
