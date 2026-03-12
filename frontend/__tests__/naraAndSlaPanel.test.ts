/**
 * Item 44 Phase 7/8 — NARA metadata and SLA panel frontend coverage.
 *
 * Tests are source-level (readFileSync) because projects/[id]/index.tsx is too
 * large to render in isolation. These guards verify:
 *   - NARA state fields are declared
 *   - NARA data is loaded from project API response
 *   - NARA save function posts to the correct endpoint with all four fields
 *   - SLA summary/deadlines queries use the correct project-scoped endpoints
 *   - SLA reminders endpoint is wired correctly
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const page = readFileSync(
  join(REPO_ROOT, "frontend/pages/projects/[id]/index.tsx"),
  "utf8",
);

// ---------------------------------------------------------------------------
// NARA Metadata — Phase 7
// ---------------------------------------------------------------------------

describe("NARA metadata — state and load", () => {
  it("declares naraScheduleNumber state", () => {
    expect(page).toContain("naraScheduleNumber");
    expect(page).toContain("setNaraScheduleNumber");
  });

  it("declares naraDispositionAuthority state", () => {
    expect(page).toContain("naraDispositionAuthority");
    expect(page).toContain("setNaraDispositionAuthority");
  });

  it("declares naraRetentionPeriod state", () => {
    expect(page).toContain("naraRetentionPeriod");
    expect(page).toContain("setNaraRetentionPeriod");
  });

  it("declares naraRecordSeries state", () => {
    expect(page).toContain("naraRecordSeries");
    expect(page).toContain("setNaraRecordSeries");
  });

  it("loads nara_schedule_number from project API data", () => {
    expect(page).toContain("nara_schedule_number");
    expect(page).toMatch(/setNaraScheduleNumber.*nara_schedule_number/s);
  });

  it("loads nara_disposition_authority from project API data", () => {
    expect(page).toMatch(/setNaraDispositionAuthority.*nara_disposition_authority/s);
  });

  it("loads nara_retention_period from project API data", () => {
    expect(page).toMatch(/setNaraRetentionPeriod.*nara_retention_period/s);
  });

  it("loads nara_record_series from project API data", () => {
    expect(page).toMatch(/setNaraRecordSeries.*nara_record_series/s);
  });
});

describe("NARA metadata — save round trip", () => {
  it("includes all four NARA fields in the save payload", () => {
    // All four must appear in the same PUT request body for the save to work.
    expect(page).toContain("nara_schedule_number:");
    expect(page).toContain("nara_disposition_authority:");
    expect(page).toContain("nara_retention_period:");
    expect(page).toContain("nara_record_series:");
  });

  it("save uses PUT method", () => {
    // The NARA save should use PUT (partial project update).
    const naraSection = page.slice(page.indexOf("nara_schedule_number:") - 500);
    expect(naraSection.slice(0, 1000)).toContain("PUT");
  });

  it("shows success toast after NARA save", () => {
    expect(page).toContain("NARA metadata saved");
  });

  it("shows error toast when NARA save fails", () => {
    expect(page).toContain("Failed to save NARA metadata");
  });
});

// ---------------------------------------------------------------------------
// SLA Panel — Phase 8
// ---------------------------------------------------------------------------

describe("SLA panel — endpoint wiring", () => {
  it("queries /projects/{id}/sla-summary for SLA overview data", () => {
    expect(page).toContain("/sla-summary");
    expect(page).toMatch(/projects\/\$\{id\}\/sla-summary|sla-summary.*id/s);
  });

  it("queries /projects/{id}/sla-deadlines for per-reviewer deadlines", () => {
    expect(page).toContain("/sla-deadlines");
    expect(page).toMatch(/projects\/\$\{id\}\/sla-deadlines|sla-deadlines.*id/s);
  });

  it("run-sla-reminders endpoint is wired for manual SLA reminder dispatch", () => {
    expect(page).toContain("run-sla-reminders");
  });

  it("SLA reminder uses POST method", () => {
    expect(page).toMatch(/run-sla-reminders.*POST|POST.*run-sla-reminders/s);
  });

  it("SLA summary is conditionally rendered (only when data is present)", () => {
    // Should check slaSummary before rendering to avoid empty panels.
    expect(page).toMatch(/slaSummary && slaSummary\.total/);
  });

  it("SLA deadline data is fetched using the project id query key", () => {
    expect(page).toMatch(/queryKey.*sla-deadlines.*id|sla-deadlines.*queryKey.*id/s);
  });
});

describe("SLA panel — SLA summary shape", () => {
  it("SLASummary interface includes a total field", () => {
    expect(page).toContain("total:");
    // The slaSummary.total check guards the render.
    expect(page).toContain("slaSummary.total");
  });
});
