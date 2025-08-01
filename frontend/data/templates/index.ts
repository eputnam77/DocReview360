import FAA_AC_TEMPLATE from "../tiptapTemplates/faa_ac_template";

const TEMPLATES = [
  {
    id: "faa_ac",
    label: "FAA Advisory Circular (TipTap)",
    content: FAA_AC_TEMPLATE,
    type: "tiptap",
  },
  {
    id: "demo_tiptap",
    label: "Demo Memo (TipTap)",
    content: `
      <h1 style='text-align:center;'>Demo Memo</h1>
      <p>Date: [YYYY-MM-DD]</p>
      <h2>Summary</h2>
      <p>[Brief summary of the memo]</p>
      <h2>Details</h2>
      <ul><li>Point 1</li><li>Point 2</li></ul>
      <h2>Conclusion</h2>
      <p>[Conclusion text]</p>
    `,
    type: "tiptap",
  },
  {
    id: "demo_word",
    label: "Demo Letter (Word .docx)",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Demo Letter</w:t></w:r></w:p>
    <w:p><w:r><w:t>Date: [YYYY-MM-DD]</w:t></w:r></w:p>
    <w:p><w:r><w:t>Dear [Recipient],</w:t></w:r></w:p>
    <w:p><w:r><w:t>This is a demo letter template for Word (.docx/.dotx).</w:t></w:r></w:p>
    <w:p><w:r><w:t>Sincerely,</w:t></w:r></w:p>
    <w:p><w:r><w:t>[Your Name]</w:t></w:r></w:p>
  </w:body>
</w:document>`,
    type: "word",
  },
];

export default TEMPLATES;
