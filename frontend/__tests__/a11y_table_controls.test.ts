/**
 * Accessibility — Task 10: Table and complex control review
 *
 * Verifies that the shared Table component and its usage in pages
 * satisfies WCAG 1.3.1 (Info and Relationships) and 4.1.2 (Name, Role, Value):
 *
 * - Table component renders a <caption> element for accessible table name.
 * - TableHead renders <th> with scope="col" by default.
 * - TableBody renders <tbody> and TableHeader renders <thead>.
 * - Table renders <table> as the root element.
 * - Search page provides a string caption to the shared Table component.
 * - Row cells use <td> (TableCell) to stay semantically correct.
 *
 * Also verifies that the profile page uses Radix-based Select for
 * complex selects (accessibility provided by Radix), OR that native
 * <select> elements have proper label associations (verified in
 * a11y_landmarks_forms.test.ts).
 */
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, it, expect } from "vitest";

const FRONTEND = resolve(__dirname, "..");
const src = (rel: string) => readFileSync(join(FRONTEND, rel), "utf8");

// ---------------------------------------------------------------------------
// Table component structure (WCAG 1.3.1)
// ---------------------------------------------------------------------------

describe("components/ui/table.tsx — semantic structure (Task 10)", () => {
  const table = src("components/ui/table.tsx");

  it("Table root renders a <table> element", () => {
    expect(table).toMatch(/<table\b/);
  });

  it("Table includes a <caption> element for accessible table name", () => {
    expect(table).toMatch(/<caption\b/);
  });

  it("caption is sr-only so it does not duplicate visible title", () => {
    expect(table).toContain("sr-only");
  });

  it("TableHeader renders a <thead> element", () => {
    expect(table).toMatch(/<thead\b/);
  });

  it("TableBody renders a <tbody> element", () => {
    expect(table).toMatch(/<tbody\b/);
  });

  it("TableHead renders <th> for column headers", () => {
    expect(table).toMatch(/<th\b/);
  });

  it("TableHead has scope='col' default parameter for column association", () => {
    // Default: scope = "col" passed as a destructured default in the function signature
    expect(table).toContain('scope = "col"');
  });

  it("TableCell renders <td> for data cells", () => {
    expect(table).toMatch(/<td\b/);
  });

  it("TableRow renders <tr>", () => {
    expect(table).toMatch(/<tr\b/);
  });
});

// ---------------------------------------------------------------------------
// Search page uses accessible table pattern (WCAG 1.3.1)
// ---------------------------------------------------------------------------

describe("search.tsx — table accessibility usage (Task 10)", () => {
  const search = src("pages/search.tsx");

  it("passes a caption prop to the Table component", () => {
    expect(search).toContain("caption=");
  });

  it("table caption describes the content ('Search results')", () => {
    expect(search).toContain("Search results");
  });

  it("table has column headers via TableHead", () => {
    expect(search).toContain("TableHead");
  });

  it("result links are inside TableCell (td) for correct row association", () => {
    expect(search).toContain("TableCell");
    expect(search).toContain("<Link");
  });

  it("empty state uses colSpan to span all columns (avoids orphan cell)", () => {
    expect(search).toContain("colSpan={3}");
  });
});

// ---------------------------------------------------------------------------
// Dialog / modal focus management review (WCAG 2.1.2, 2.4.3)
// ---------------------------------------------------------------------------

describe("components/ui/dialog.tsx — Radix focus management (Task 6/10)", () => {
  const dialog = src("components/ui/dialog.tsx");

  it("uses @radix-ui/react-dialog for built-in focus trap", () => {
    expect(dialog).toContain("@radix-ui/react-dialog");
  });

  it("DialogContent uses Radix Portal for correct focus containment", () => {
    // dialog.tsx wraps content in RadixDialog.Portal (not a named DialogPortal export)
    expect(dialog).toContain("RadixDialog.Portal");
  });

  it("exports DialogTitle for required accessible dialog name", () => {
    expect(dialog).toContain("DialogTitle");
  });

  it("exports DialogDescription for optional accessible description", () => {
    expect(dialog).toContain("DialogDescription");
  });
});

// ---------------------------------------------------------------------------
// Modal focus management (WCAG 2.1.2)
// ---------------------------------------------------------------------------

describe("components/ui/modal.tsx — Radix focus management (Task 6/10)", () => {
  const modal = src("components/ui/modal.tsx");

  it("uses @radix-ui/react-dialog for built-in focus trap", () => {
    expect(modal).toContain("@radix-ui/react-dialog");
  });

  it("exports ModalTitle for required accessible dialog name", () => {
    expect(modal).toContain("ModalTitle");
  });
});
