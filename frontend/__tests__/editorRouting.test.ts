import {
  buildDocumentEditorUrl,
  buildProjectEditorUrl,
  normalizeEditorProvider,
} from "@/lib/editorRouting";
import {
  readBooleanQueryParam,
  readSingleQueryParam,
} from "@/lib/editorQuery";

describe("editor routing helpers", () => {
  it("normalizes supported editor aliases and defaults to ckeditor5", () => {
    expect(normalizeEditorProvider("ckeditor")).toBe("ckeditor5");
    expect(normalizeEditorProvider("cke5")).toBe("ckeditor5");
    expect(normalizeEditorProvider("TipTap")).toBe("tiptap");
    expect(normalizeEditorProvider(" ONLYOFFICE ")).toBe("onlyoffice");
    expect(normalizeEditorProvider("unknown")).toBe("ckeditor5");
    expect(normalizeEditorProvider(undefined)).toBe("ckeditor5");
  });

  it("builds project editor urls with readonly and anchor support", () => {
    expect(
      buildProjectEditorUrl("ckeditor", "proj-1", {
        readonly: true,
        anchor: "42:57",
      }),
    ).toBe("/editors/ckeditor5?projectId=proj-1&readonly=1&anchor=42%3A57");
  });

  it("builds document editor urls for backup routes", () => {
    expect(
      buildDocumentEditorUrl("onlyoffice", "doc-1", { anchor: "11:19" }),
    ).toBe("/editors/onlyoffice?id=doc-1&anchor=11%3A19");
  });
});

describe("editor query helpers", () => {
  it("reads the first non-empty query value", () => {
    expect(readSingleQueryParam([" doc-1 ", "doc-2"])).toBe("doc-1");
    expect(readSingleQueryParam("   ")).toBeUndefined();
  });

  it("parses boolean editor query flags", () => {
    expect(readBooleanQueryParam("1")).toBe(true);
    expect(readBooleanQueryParam("true")).toBe(true);
    expect(readBooleanQueryParam(["yes"])).toBe(true);
    expect(readBooleanQueryParam("0")).toBe(false);
    expect(readBooleanQueryParam(undefined)).toBe(false);
  });
});
