// Word template configurations
export interface WordTemplate {
  id: string;
  label: string;
  description: string;
  url: string;
  type: 'docx' | 'dotx';
  category: string;
}

export const WORD_TEMPLATES: WordTemplate[] = [
  {
    id: "business_letter",
    label: "Business Letter Template",
    description: "Professional business letter format with company header and signature block",
    url: "/templates/word/business_letter_template.docx",
    type: "docx",
    category: "correspondence"
  },
  {
    id: "memo_template",
    label: "Memo Template",
    description: "Standard memorandum format with TO, FROM, DATE, and SUBJECT fields",
    url: "/templates/word/memo_template.docx",
    type: "docx",
    category: "correspondence"
  },
  {
    id: "report_template",
    label: "Report Template",
    description: "Formal report template with table of contents and section headers",
    url: "/templates/word/report_template.docx",
    type: "docx",
    category: "reports"
  },
  {
    id: "proposal_template",
    label: "Proposal Template",
    description: "Professional proposal template with executive summary and appendices",
    url: "/templates/word/proposal_template.docx",
    type: "docx",
    category: "business"
  },
  {
    id: "meeting_minutes",
    label: "Meeting Minutes Template",
    description: "Structured meeting minutes with action items and follow-up tasks",
    url: "/templates/word/meeting_minutes_template.docx",
    type: "docx",
    category: "meetings"
  }
];

export const getWordTemplate = (id: string): WordTemplate | undefined => {
  return WORD_TEMPLATES.find(template => template.id === id);
};

export const getWordTemplatesByCategory = (category: string): WordTemplate[] => {
  return WORD_TEMPLATES.filter(template => template.category === category);
};

export const getAllWordTemplates = (): WordTemplate[] => {
  return WORD_TEMPLATES;
};
