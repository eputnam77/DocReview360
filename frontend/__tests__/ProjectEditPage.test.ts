import { describe, expect, it } from "vitest";
import {
  buildEditProjectPayload,
  readProjectUpdateError,
  resolveEditWorkflowSuggestion,
  type EditProjectPayloadArgs,
} from "../pages/projects/[id]/edit";

function baseArgs(overrides: Partial<EditProjectPayloadArgs> = {}): EditProjectPayloadArgs {
  return {
    docNumber: "DOC-1",
    title: "Project One",
    docType: "Policy",
    phase: "draft",
    description: "desc",
    sme: "alice",
    selectedWorkflow: "review",
    username: "alice",
    isAdmin: false,
    ...overrides,
  };
}

describe("buildEditProjectPayload", () => {
  it("blocks non-admin reassignment to another user", () => {
    const result = buildEditProjectPayload(baseArgs({ sme: "bob", isAdmin: false }));

    expect(result.error).toBe("You do not have permission to assign this project to another user.");
    expect(result.payload).toBeUndefined();
  });

  it("returns payload with optional user and workflow fields", () => {
    const result = buildEditProjectPayload(baseArgs({ sme: "  ", selectedWorkflow: "" }));

    expect(result.error).toBeUndefined();
    expect(result.payload).toEqual({
      name: "Project One",
      doc_type: "Policy",
      phase: "draft",
      description: "desc",
    });
  });

  it("keeps user/workflow when provided", () => {
    const result = buildEditProjectPayload(baseArgs());

    expect(result.error).toBeUndefined();
    expect(result.payload).toEqual({
      name: "Project One",
      doc_type: "Policy",
      phase: "draft",
      description: "desc",
      user: "alice",
      workflow: "review",
    });
  });
});

describe("readProjectUpdateError", () => {
  it("prefers backend detail field", async () => {
    const message = await readProjectUpdateError({
      status: 409,
      json: async () => ({ detail: "Workflow already assigned to another project" }),
      text: async () => "",
    });

    expect(message).toBe("Workflow already assigned to another project");
  });

  it("falls back to response text when json parsing fails", async () => {
    const message = await readProjectUpdateError({
      status: 500,
      json: async () => {
        throw new Error("invalid json");
      },
      text: async () => "Backend exploded",
    });

    expect(message).toBe("Backend exploded");
  });
});

describe("resolveEditWorkflowSuggestion", () => {
  const docTypeDefaults = {
    Policy: "doc-workflow",
  } as Record<string, string | undefined>;
  const phaseDefaults = {
    "Draft Development": "phase-workflow",
  } as Record<string, string | undefined>;

  it("prefers the document type default workflow", () => {
    const result = resolveEditWorkflowSuggestion(
      "Policy",
      "Draft Development",
      docTypeDefaults,
      phaseDefaults,
    );
    expect(result).toBe("doc-workflow");
  });

  it("uses phase default when doc type has no default", () => {
    const result = resolveEditWorkflowSuggestion(
      "FAQ",
      "Draft Development",
      docTypeDefaults,
      phaseDefaults,
    );
    expect(result).toBe("phase-workflow");
  });
});
