/**
 * FSV Integration UX Tasks — DR-FSV-1 through DR-FSV-12
 *
 * Source-level tests verifying every item in FSV_INTEGRATION_UX_TASKS.md.
 * Tests read the TypeScript / Python source and assert that key patterns exist
 * or have been removed, following the same convention as fsvEditorAndProject.test.ts.
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");
const FRONTEND = join(REPO_ROOT, "frontend");
const SRC = join(REPO_ROOT, "src", "docreview360");

function src(relPath: string): string {
  return readFileSync(join(FRONTEND, relPath), "utf8");
}

// ---------------------------------------------------------------------------
// DR-FSV-1: FSV brand tokens in branding.ts
// ---------------------------------------------------------------------------

describe("DR-FSV-1: FSV brand tokens (branding.ts)", () => {
  const branding = src("state/branding.ts");

  it("exports FSV_BRAND_TOKENS constant", () => {
    expect(branding).toContain("export const FSV_BRAND_TOKENS");
  });

  it("FSV_BRAND_TOKENS includes primaryColor from brand-tokens.json", () => {
    expect(branding).toContain("primaryColor");
    // Value matches brand-tokens.json primary.default
    expect(branding).toContain("#4F46E5");
  });

  it("FSV_BRAND_TOKENS includes all severity color slots", () => {
    expect(branding).toContain("severityError");
    expect(branding).toContain("severityWarning");
    expect(branding).toContain("severityInfo");
    expect(branding).toContain("severitySuccess");
  });

  it("BrandingState interface has fsvPrimaryColor field", () => {
    expect(branding).toContain("fsvPrimaryColor");
  });

  it("fsvPrimaryColor defaults to FSV_BRAND_TOKENS.primaryColor", () => {
    expect(branding).toMatch(/fsvPrimaryColor.*FSV_BRAND_TOKENS\.primaryColor/s);
  });

  it("initialize() sets fsvPrimaryColor (org override falls back to token)", () => {
    const initBlock = branding.slice(branding.indexOf("async initialize"));
    expect(initBlock).toContain("fsvPrimaryColor");
    expect(initBlock).toContain("FSV_BRAND_TOKENS.primaryColor");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-2: theme=light passed to FSV API calls (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-2: theme=light header on FSV API calls (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("appends theme=light to /tools/checker form data", () => {
    expect(page).toMatch(/formData\.append.*theme.*light/);
  });

  it("sets X-FSV-Theme: light header on /tools/checker POST", () => {
    expect(page).toContain("X-FSV-Theme");
    expect(page).toContain("light");
  });

  it("passes X-FSV-Theme: light to /documents/validate as well", () => {
    expect(page).toMatch(/X-FSV-Theme.*light/);
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-3: Severity colors aligned with DocReview360 system (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-3: Severity colors use text-red-600/amber-600/blue-600 (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("scoreColor uses text-amber-600 (not text-yellow-600) for mid range", () => {
    expect(page).toContain("text-amber-600");
    expect(page).not.toContain("text-yellow-600");
  });

  it("scoreBg uses bg-amber-50/border-amber-200 (not bg-yellow-50)", () => {
    expect(page).toContain("bg-amber-50");
    expect(page).not.toContain("bg-yellow-50");
  });

  it("error severity uses text-red-600", () => {
    expect(page).toContain("text-red-600");
  });

  it("SeverityBadge component renders error, warning, info variants", () => {
    expect(page).toContain("SeverityBadge");
    expect(page).toContain('"error"');
    expect(page).toContain('"warning"');
    expect(page).toContain('"info"');
  });

  it("no deprecated orange-400 / yellow-400 border/dot colors remain", () => {
    expect(page).not.toContain("border-orange-400");
    expect(page).not.toContain("bg-orange-400");
    expect(page).not.toContain("bg-yellow-400");
    expect(page).not.toContain("border-yellow-300");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-4: Zero-issues success state (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-4: Zero-issues success state (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("renders SuccessBanner component", () => {
    expect(page).toContain("SuccessBanner");
  });

  it("success banner shows 'No style issues found' heading", () => {
    expect(page).toContain("No style issues found");
  });

  it("success banner includes green CheckCircle icon", () => {
    expect(page).toContain("CheckCircle");
    expect(page).toContain("text-green-600");
  });

  it("success banner explains which categories ran", () => {
    // Banner receives categories prop / list
    expect(page).toMatch(/categories.*join|ranCategories/s);
  });

  it("system doc result checks totalIssueCount before showing success state", () => {
    expect(page).toContain("totalIssueCount");
    expect(page).toMatch(/totalIssueCount.*===.*0/);
  });

  it("upload results show success when parsedFindings is empty", () => {
    expect(page).toContain("parsedFindings");
    expect(page).toMatch(/parsedFindings\.length.*===.*0|parsedFindings\.length.*0/);
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-5: Actionable fix instructions in results display (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-5: Structured findings with authority + how-to-fix (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("Finding interface has severity, message, authority, fix, category fields", () => {
    expect(page).toContain("interface Finding");
    expect(page).toContain("severity");
    expect(page).toContain("authority");
    expect(page).toContain("fix");
    expect(page).toContain("category");
  });

  it("parseFindingsFromCheckResult function exists", () => {
    expect(page).toContain("parseFindingsFromCheckResult");
  });

  it("parser extracts authority from issue objects", () => {
    expect(page).toMatch(/authority.*obj\.authority|obj\.authority.*authority/s);
  });

  it("parser provides FAA Order 1320.46D as default authority for acronyms", () => {
    expect(page).toContain("FAA Order 1320.46D");
  });

  it("parser provides AP Style Guide as default authority for style issues", () => {
    expect(page).toContain("AP Style Guide");
  });

  it("HowToFix component or 'How to fix' label is rendered", () => {
    expect(page).toContain("How to fix");
  });

  it("FindingsDisplay renders SeverityBadge per finding", () => {
    expect(page).toContain("FindingsDisplay");
    expect(page).toContain("SeverityBadge");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-6: Per-category collapsible sections with count badges (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-6: Collapsible sections with count badges (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("CollapsibleSection component is defined", () => {
    expect(page).toContain("CollapsibleSection");
  });

  it("uses <details> element for collapse behaviour", () => {
    expect(page).toContain("<details");
    expect(page).toContain("<summary");
  });

  it("shows count badge per category", () => {
    expect(page).toMatch(/count.*issue|issue.*count/i);
  });

  it("system doc results use CollapsibleSection for Acronym Issues", () => {
    expect(page).toMatch(/CollapsibleSection.*Acronym|Acronym.*CollapsibleSection/s);
  });

  it("system doc results use CollapsibleSection for Style Issues", () => {
    expect(page).toMatch(/CollapsibleSection.*Style|Style.*CollapsibleSection/s);
  });

  it("system doc results use CollapsibleSection for Heading Structure", () => {
    expect(page).toMatch(/CollapsibleSection.*Heading|Heading.*CollapsibleSection/s);
  });

  it("FindingsDisplay groups findings by category for upload results", () => {
    expect(page).toContain("groupFindingsByCategory");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-7: Loading skeleton while FSV processes (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-7: Loading skeleton (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("LoadingSkeleton component is defined", () => {
    expect(page).toContain("LoadingSkeleton");
  });

  it("skeleton uses animate-pulse class", () => {
    expect(page).toContain("animate-pulse");
  });

  it("skeleton shown while isLoading in upload tab", () => {
    expect(page).toMatch(/isLoading.*LoadingSkeleton|LoadingSkeleton.*isLoading/s);
  });

  it("skeleton shown while validating in system doc tab", () => {
    expect(page).toMatch(/validating.*LoadingSkeleton|LoadingSkeleton.*validating/s);
  });

  it("skeleton has aria-busy for accessibility", () => {
    expect(page).toContain('aria-busy="true"');
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-8: FSV service status banner (document-quality.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-8: FSV service unavailable banner (document-quality.tsx)", () => {
  const page = src("pages/tools/document-quality.tsx");

  it("calls GET /fsv/status on mount", () => {
    expect(page).toContain("/fsv/status");
    expect(page).toContain("useEffect");
  });

  it("FsvUnavailableBanner component is defined", () => {
    expect(page).toContain("FsvUnavailableBanner");
  });

  it("banner text is 'Federal Style Validator service is currently unavailable'", () => {
    expect(page).toContain(
      "Federal Style Validator service is currently unavailable.",
    );
  });

  it("banner includes 'Contact your administrator' instruction", () => {
    expect(page).toContain("Contact your administrator");
  });

  it("admin users see a link to reconfigure the FSV URL", () => {
    expect(page).toMatch(/isAdmin.*href|href.*isAdmin/s);
    expect(page).toContain("/tools");
  });

  it("fsvStatus state is declared", () => {
    expect(page).toContain("fsvStatus");
    expect(page).toContain("FsvServiceStatus");
  });

  it("banner is rendered only when fsvStatus is 'unavailable'", () => {
    expect(page).toMatch(/fsvStatus.*===.*unavailable|unavailable.*fsvStatus/);
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-9: Quality score pill uses semantic colors + labels (tiptap.tsx)
// ---------------------------------------------------------------------------

describe("DR-FSV-9: Quality pill semantic colors and labels (tiptap.tsx)", () => {
  const tiptap = src("pages/editors/tiptap.tsx");

  it("pill uses text-green-600 for score >= 0.8", () => {
    expect(tiptap).toContain("text-green-600");
    expect(tiptap).toMatch(/0\.8.*text-green-600|text-green-600.*0\.8/s);
  });

  it("pill uses text-amber-600 for score 0.5-0.79", () => {
    expect(tiptap).toContain("text-amber-600");
    expect(tiptap).toMatch(/0\.5.*text-amber-600|text-amber-600.*0\.5/s);
  });

  it("pill uses text-red-600 for score < 0.5", () => {
    expect(tiptap).toContain("text-red-600");
  });

  it("pill shows label 'Good' for high scores", () => {
    expect(tiptap).toContain("Good");
  });

  it("pill shows label 'Needs attention' for mid scores", () => {
    expect(tiptap).toContain("Needs attention");
  });

  it("pill shows label 'Issues found' for low scores", () => {
    expect(tiptap).toContain("Issues found");
  });

  it("pill no longer uses legacy text-green-800/amber-800/red-800 colors", () => {
    // The quality pill section should use -600 not -800 variants
    const pillSection = tiptap.slice(
      tiptap.indexOf("DR-FSV-9"),
      tiptap.indexOf("DR-FSV-9") + 800,
    );
    expect(pillSection).not.toContain("text-green-800");
    expect(pillSection).not.toContain("text-amber-800");
    expect(pillSection).not.toContain("text-red-800");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-10: Quality pill links to checker page; checker accepts document_id
// ---------------------------------------------------------------------------

describe("DR-FSV-10: Quality pill is a Link; checker accepts document_id query param", () => {
  const tiptap = src("pages/editors/tiptap.tsx");
  const page = src("pages/tools/document-quality.tsx");

  it("tiptap imports Link from next/link", () => {
    expect(tiptap).toContain("from \"next/link\"");
  });

  it("quality pill is wrapped in a Link component", () => {
    expect(tiptap).toMatch(/<Link.*href.*document-quality|href.*document-quality.*<Link/s);
  });

  it("Link href includes document_id query param", () => {
    expect(tiptap).toContain("document_id");
    expect(tiptap).toContain("/tools/document-quality");
  });

  it("Link href encodes document_id value", () => {
    expect(tiptap).toContain("encodeURIComponent");
  });

  it("document-quality.tsx reads router.query.document_id", () => {
    expect(page).toContain("router.query.document_id");
  });

  it("document-quality.tsx auto-switches to system tab when document_id is set", () => {
    expect(page).toMatch(/setActiveTab.*system|system.*setActiveTab/);
    expect(page).toMatch(/setSelectedDocId.*qid|qid.*setSelectedDocId/);
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-11: Consistent "Federal Style Validator" terminology
// ---------------------------------------------------------------------------

describe("DR-FSV-11: Consistent terminology — 'Federal Style Validator'", () => {
  const marketplace = src("pages/configuration/plugin-marketplace.tsx");
  const docQuality = src("pages/tools/document-quality.tsx");
  const tools = src("pages/tools/index.tsx");

  it("plugin-marketplace shows 'Federal Style Validator' (not 'FedStyleValidator') as plugin name", () => {
    // The user-facing name field in both the loaded list and the fallback list
    expect(marketplace).toMatch(/name:\s*["']Federal Style Validator["']/);
    // Old short name should not appear in user-facing name field
    expect(marketplace).not.toMatch(/name:\s*["']FedStyleValidator["']/);
  });

  it("plugin-marketplace description uses 'Federal Style Validator' (not 'FedStyleValidator')", () => {
    expect(marketplace).not.toContain("FedStyleValidator and SCDocBuilder");
    expect(marketplace).toContain("Federal Style Validator and SCDocBuilder");
  });

  it("document-quality.tsx uses 'Federal Style Validator' in status messages", () => {
    expect(docQuality).toContain("Connected to Federal Style Validator backend");
  });

  it("document-quality.tsx has no user-facing 'FedStyleValidator' (technical id OK)", () => {
    // The only acceptable uses are ID strings (fedstylevalidator) — not display text
    const userFacing = docQuality.replace(/id.*fedstylevalidator/gi, "");
    expect(userFacing).not.toContain("FedStyleValidator");
  });

  it("tools/index.tsx section headings say 'Federal Style Validator'", () => {
    expect(tools).toContain("Federal Style Validator — On-Save Validation");
    expect(tools).toContain("Federal Style Validator — Service URL");
  });
});

// ---------------------------------------------------------------------------
// DR-FSV-12: "Test connection" button in tools/index.tsx
// ---------------------------------------------------------------------------

describe("DR-FSV-12: Test connection button in admin FSV URL settings", () => {
  const tools = src("pages/tools/index.tsx");

  it("testFsvConnection function is defined", () => {
    expect(tools).toContain("testFsvConnection");
  });

  it("testFsvConnection calls GET /fsv/status", () => {
    expect(tools).toContain("/fsv/status");
    expect(tools).toMatch(/testFsvConnection[\s\S]*?\/fsv\/status/);
  });

  it("Test connection button is rendered", () => {
    expect(tools).toContain("Test connection");
  });

  it("button is disabled while testingFsvConnection is true", () => {
    expect(tools).toContain("testingFsvConnection");
    expect(tools).toMatch(/disabled.*testingFsvConnection|testingFsvConnection.*disabled/s);
  });

  it("fsvConnectionStatus state tracks 'ok' | 'fail' result", () => {
    expect(tools).toContain("fsvConnectionStatus");
    expect(tools).toContain('"ok"');
    expect(tools).toContain('"fail"');
  });

  it("shows inline 'reachable' message on success", () => {
    expect(tools).toMatch(/reachable|Federal Style Validator is reachable/i);
  });

  it("shows inline error message on failure", () => {
    expect(tools).toContain("Unreachable");
  });

  it("connection result clears when URL input is changed", () => {
    expect(tools).toMatch(/setFsvConnectionStatus.*idle|idle.*setFsvConnectionStatus/);
  });
});
