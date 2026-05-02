import { describe, expect, it } from "vitest";
import { filenameFromContentDisposition } from "../pages/tools/converter";

describe("filenameFromContentDisposition", () => {
  it("extracts quoted filenames from download responses", () => {
    expect(filenameFromContentDisposition('attachment; filename="sample_converted.pdf"')).toBe(
      "sample_converted.pdf",
    );
  });

  it("extracts RFC 5987 encoded filenames", () => {
    expect(filenameFromContentDisposition("attachment; filename*=UTF-8''Policy%20Memo.pdf")).toBe(
      "Policy Memo.pdf",
    );
  });

  it("returns null when the header does not include a filename", () => {
    expect(filenameFromContentDisposition("attachment")).toBeNull();
    expect(filenameFromContentDisposition(null)).toBeNull();
  });
});
