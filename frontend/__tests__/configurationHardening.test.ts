import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");

function src(...segments: string[]): string {
  return readFileSync(join(REPO_ROOT, ...segments), "utf8");
}

describe("configuration production hardening", () => {
  it("keeps workflow user Select values non-empty and description optional", () => {
    const createWorkflow = src("frontend", "pages", "configuration", "workflows", "new.tsx");
    const editWorkflow = src("frontend", "pages", "configuration", "workflows", "edit.tsx");

    expect(createWorkflow).toContain('const NONE_USER_VALUE = "__none__";');
    expect(createWorkflow).toContain("<SelectItem value={NONE_USER_VALUE}>None</SelectItem>");
    expect(createWorkflow).not.toContain('<SelectItem value="">None</SelectItem>');
    expect(createWorkflow).toContain("disabled={!name.trim() || steps.length === 0}");
    expect(createWorkflow).not.toContain("disabled={!name || !description || steps.length === 0}");
    expect(editWorkflow).toContain("disabled={!name.trim() || steps.length === 0}");
    expect(editWorkflow).not.toContain("disabled={!name || !description || steps.length === 0}");
  });

  it("does not hide partial workflow attachment failures", () => {
    const createWorkflow = src("frontend", "pages", "configuration", "workflows", "new.tsx");

    expect(createWorkflow).toContain("attachmentFailures");
    expect(createWorkflow).toContain("Workflow saved, but attachment failed for:");
    expect(createWorkflow).not.toContain("ignore errors in development");
  });

  it("preserves document type default workflow when changing phases", () => {
    const documentTypes = src("frontend", "pages", "configuration", "document-types.tsx");

    expect(documentTypes).toContain(
      "default_workflow_template_id: docType.default_workflow_template_id || null",
    );
  });
});
