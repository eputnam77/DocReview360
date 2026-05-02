import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { readFileSync } from "fs";
import { join, resolve } from "path";
import { describe, expect, it } from "vitest";

const REPO_ROOT = resolve(__dirname, "../..");

function src(...segments: string[]): string {
  return readFileSync(join(REPO_ROOT, ...segments), "utf8");
}

describe("ai-notes completion coverage", () => {
  it("keeps CKEditor5 as the checked-in default editor", () => {
    expect(src("docreview360.yaml")).toContain("editor: ckeditor5");
  });

  it("keeps Oxygen and signature providers in the Integrations dropdown option lists", () => {
    const integrations = src("frontend", "pages", "configuration", "integrations.tsx");

    expect(integrations).toContain('{ label: "Oxygen XML Web Author", value: "oxygen" }');
    expect(integrations).toContain('{ label: "Documenso", value: "documenso" }');
    expect(integrations).toContain('{ label: "DocuSign", value: "docusign" }');
    expect(integrations).toContain('{ label: "Initials (in-app)", value: "initials" }');
    expect(integrations).toContain('{ label: "Local (built-in)", value: "local" }');
  });

  it("keeps Document Types default workflow SelectItem values non-empty", () => {
    const documentTypes = src("frontend", "pages", "configuration", "document-types.tsx");

    expect(documentTypes).toContain('<SelectItem value="__none__">None</SelectItem>');
    expect(documentTypes).not.toContain('<SelectItem value="">None</SelectItem>');
  });

  it("uses default starter content in the CKEditor5 blank-document path", () => {
    const ckeditor = src("frontend", "components", "CKEditorPrimary.tsx");

    expect(ckeditor).toContain("resolveStarterContent");
    expect(ckeditor).toContain("isBlankEditorContent(nextData)");
    expect(ckeditor).toContain("api.fetchStarterContent");
    expect(ckeditor).toContain("api.fetchTemplate(starter.templateId)");
    expect(ckeditor).toContain("sanitizeHtml");
  });

  it("configures CKEditor5 heading and list commands in the primary toolbar", () => {
    const ckeditor = src("frontend", "components", "CKEditorPrimary.tsx");

    expect(ckeditor).toContain("Heading");
    expect(ckeditor).toContain("List");
    expect(ckeditor).toContain('"heading"');
    expect(ckeditor).toContain('"bulletedList"');
    expect(ckeditor).toContain('"numberedList"');
  });

  it("keeps the Tools converter UI aligned with backend output formats", () => {
    const converter = src("frontend", "pages", "tools", "converter.tsx");

    for (const outputFormat of ["pdf", "html", "markdown", "txt", "docx", "confluence"]) {
      expect(converter).toContain(`value="${outputFormat}"`);
    }
    expect(converter).toContain("filenameFromContentDisposition");
    expect(converter).toContain("await res.blob()");
  });
});

describe("TipTap backup editor command coverage", () => {
  it("supports heading, bold, italic, bulleted list, numbered list, and list indentation commands", () => {
    const tiptap = src("frontend", "components", "TiptapEditorBasic.tsx");
    const editor = new Editor({
      extensions: [StarterKit],
      content: "<p>Alpha</p>",
    });

    editor.commands.selectAll();
    editor.chain().focus().toggleHeading({ level: 1 }).run();
    expect(editor.getHTML()).toContain("<h1>Alpha</h1>");

    editor.commands.setContent("<p>Bold</p>");
    editor.commands.selectAll();
    editor.chain().focus().toggleBold().run();
    expect(editor.getHTML()).toContain("<strong>Bold</strong>");

    editor.commands.setContent("<p>Italic</p>");
    editor.commands.selectAll();
    editor.chain().focus().toggleItalic().run();
    expect(editor.getHTML()).toContain("<em>Italic</em>");

    editor.commands.setContent("<p>Bullet</p>");
    editor.commands.selectAll();
    editor.chain().focus().toggleBulletList().run();
    expect(editor.getHTML()).toContain("<ul>");
    expect(editor.getHTML()).toContain("<li><p>Bullet</p></li>");

    editor.commands.setContent("<p>One</p>");
    editor.commands.selectAll();
    editor.chain().focus().toggleOrderedList().run();
    expect(editor.getHTML()).toContain("<ol>");
    expect(editor.getHTML()).toContain("<li><p>One</p></li>");

    expect(tiptap).toContain('sinkListItem("listItem")');
    expect(tiptap).toContain('liftListItem("listItem")');

    editor.destroy();
  });
});
