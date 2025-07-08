// frontend/data/codexTemplates/faa_ac_template.js
const FAA_AC_TEMPLATE = {
  time: Date.now(),
  blocks: [
    {
      type: "header",
      data: {
        text: "Advisory Circular",
        level: 1,
      },
    },
    {
      type: "header",
      data: {
        text: "AC 20-XXX",
        level: 2,
      },
    },
    {
      type: "paragraph",
      data: {
        text: "<i>Subject: [Subject of Advisory Circular]</i>",
      },
    },
    {
      type: "paragraph",
      data: {
        text: "<span style='color:gray;font-size:0.9em;'>Date: [YYYY-MM-DD] &nbsp;&nbsp; Initiated by: [FAA Office]</span>",
      },
    },
    { type: "delimiter", data: {} },
    {
      type: "header", data: { text: "1. Purpose", level: 2 },
    },
    {
      type: "paragraph",
      data: {
        text: "This advisory circular (AC) provides guidance for [brief statement of purpose].",
      },
    },
    {
      type: "header", data: { text: "2. Applicability", level: 2 },
    },
    {
      type: "paragraph",
      data: { text: "This AC applies to [describe applicability/audience]." },
    },
    {
      type: "header", data: { text: "3. Related Documents", level: 2 },
    },
    {
      type: "list",
      data: {
        style: "unordered",
        items: [
          "Title 14 of the Code of Federal Regulations (14 CFR) part [part number]",
          "[Other references or documents]",
        ],
      },
    },
    {
      type: "header", data: { text: "4. Background", level: 2 },
    },
    {
      type: "paragraph",
      data: {
        text: "[Background information on the need for the AC, relevant history, and supporting data.]",
      },
    },
    {
      type: "header", data: { text: "5. Guidance", level: 2 },
    },
    {
      type: "header", data: { text: "5.1 General", level: 3 },
    },
    {
      type: "paragraph",
      data: { text: "[General guidance or policy statement.]" },
    },
    {
      type: "header", data: { text: "5.2 Procedures", level: 3 },
    },
    {
      type: "list",
      data: {
        style: "ordered",
        items: [
          "Step one: [Describe procedure step one]",
          "Step two: [Describe procedure step two]",
          "Step three: [Describe procedure step three]",
        ],
      },
    },
    {
      type: "header", data: { text: "5.3 Notes", level: 3 },
    },
    {
      type: "quote",
      data: {
        text: "Note: [Insert important note or caution.]",
        caption: "",
      },
    },
    {
      type: "header", data: { text: "6. Definitions", level: 2 },
    },
    {
      type: "list",
      data: {
        style: "unordered",
        items: [
          "<b>Term 1:</b> Definition for term 1.",
          "<b>Term 2:</b> Definition for term 2.",
        ],
      },
    },
    {
      type: "header", data: { text: "7. Contact", level: 2 },
    },
    {
      type: "paragraph",
      data: { text: "Direct questions or comments regarding this AC to [FAA Office contact information]." },
    },
    { type: "delimiter", data: {} },
    {
      type: "paragraph",
      data: {
        text: "<span style='color:gray;font-size:0.9em;'>This is an example Advisory Circular template for use in Editor.js. Replace bracketed sections with actual content.</span>",
      },
    },
  ],
  version: "2.29.1",
};

export default FAA_AC_TEMPLATE;
