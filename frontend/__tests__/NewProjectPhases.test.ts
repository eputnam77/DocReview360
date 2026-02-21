import { describe, expect, it } from "vitest";
import { mergeProjectPhases, resolveDefaultWorkflow } from "../pages/projects/new";

describe("mergeProjectPhases", () => {
  it("includes all configured phases", () => {
    const result = mergeProjectPhases(["Draft", "Review", "Final"], ["Draft"]);
    expect(result).toEqual(["Draft", "Review", "Final"]);
  });

  it("merges and de-duplicates configured and doc-type phases", () => {
    const result = mergeProjectPhases(
      ["Draft", "Review", "Final"],
      ["Review", "Publish", "  Final  "],
    );
    expect(result).toEqual(["Draft", "Review", "Final", "Publish"]);
  });
});

describe("resolveDefaultWorkflow", () => {
  const docDefaults = {
    Policy: "doc-flow",
  } as Record<string, string | undefined>;

  const phaseDefaults = {
    "Draft Development": "phase-flow",
  } as Record<string, string | undefined>;

  it("prefers document type default template", () => {
    const result = resolveDefaultWorkflow(
      "Policy",
      "Draft Development",
      docDefaults,
      phaseDefaults,
    );
    expect(result).toBe("doc-flow");
  });

  it("falls back to phase workflow template when doc type has no default", () => {
    const result = resolveDefaultWorkflow(
      "FAQ",
      "Draft Development",
      docDefaults,
      phaseDefaults,
    );
    expect(result).toBe("phase-flow");
  });

  it("returns undefined when no defaults exist", () => {
    const result = resolveDefaultWorkflow("FAQ", "Review", docDefaults, phaseDefaults);
    expect(result).toBeUndefined();
  });
});
