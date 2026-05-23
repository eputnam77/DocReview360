import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";

const FRONTEND = resolve(__dirname, "..");
const src = readFileSync(join(FRONTEND, "pages/logs/index.tsx"), "utf8");

describe("logs page route contracts", () => {
  it("does not use unsupported HEAD probes for audit entity links", () => {
    expect(src).not.toContain('method: "HEAD"');
    expect(src).toContain("`/projects/${encodeURIComponent(id)}`");
  });

  it("builds the live-log WebSocket from the configured API base", () => {
    expect(src).toContain("new URL(API, window.location.origin)");
    expect(src).toContain('apiUrl.pathname = "/ws/logs"');
  });
});
