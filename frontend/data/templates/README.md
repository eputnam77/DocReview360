# Word Template System

This directory contains the Word template system for DocReview360, allowing users to view and edit Word documents using Microsoft Office Online.

## Structure

```
frontend/data/templates/
├── wordTemplates.ts          # Template configuration and metadata
├── index.ts                  # Main template registry
└── README.md                 # This file

frontend/public/templates/word/
├── business_letter_template.docx
├── memo_template.docx
├── report_template.docx
├── proposal_template.docx
└── meeting_minutes_template.docx
```

## Available Templates

### 1. Business Letter Template
- **Type**: DOCX
- **Category**: Correspondence
- **Description**: Professional business letter format with company header and signature block
- **Use Case**: Formal business communications

### 2. Memo Template
- **Type**: DOCX
- **Category**: Correspondence
- **Description**: Standard memorandum format with TO, FROM, DATE, and SUBJECT fields
- **Use Case**: Internal communications and memos

### 3. Report Template
- **Type**: DOCX
- **Category**: Reports
- **Description**: Formal report template with table of contents and section headers
- **Use Case**: Business reports, research reports, analysis documents

### 4. Proposal Template
- **Type**: DOCX
- **Category**: Business
- **Description**: Professional proposal template with executive summary and appendices
- **Use Case**: Business proposals, project proposals, client proposals

### 5. Meeting Minutes Template
- **Type**: DOCX
- **Category**: Meetings
- **Description**: Structured meeting minutes with action items and follow-up tasks
- **Use Case**: Meeting documentation, action item tracking

## Usage

### Viewing Templates
1. Navigate to `/editors/word` in the application
2. Select a template from the sidebar
3. The template will be displayed using Microsoft Office Online viewer
4. Use the "Edit Online" button to open the template in edit mode

### Adding New Templates
1. Create a new Word document (.docx) template
2. Place it in `frontend/public/templates/word/`
3. Add the template configuration to `wordTemplates.ts`:

```typescript
{
  id: "your_template_id",
  label: "Your Template Name",
  description: "Description of the template",
  url: "/templates/word/your_template.docx",
  type: "docx",
  category: "your_category"
}
```

### Regenerating Templates
To regenerate all Word templates from the Python script:

```bash
cd DocReview360
python scripts/generate_word_templates.py
```

## Technical Details

### Template Configuration
Templates are configured in `wordTemplates.ts` with the following interface:

```typescript
interface WordTemplate {
  id: string;           // Unique identifier
  label: string;        // Display name
  description: string;  // Template description
  url: string;          // Path to the .docx file
  type: 'docx' | 'dotx'; // File type
  category: string;     // Template category
}
```

### Microsoft Office Online Integration
The system uses Microsoft's Office Online viewer to display and edit Word documents:
- **View Mode**: `https://view.officeapps.live.com/op/embed.aspx?src={document_url}`
- **Edit Mode**: `https://view.officeapps.live.com/op/embed.aspx?src={document_url}&wdStartOn=1`

### File Requirements
- Templates must be publicly accessible via HTTP/HTTPS
- Files should be in .docx or .dotx format
- Maximum file size: 10MB (Microsoft Office Online limit)

## Categories

- **Correspondence**: Letters, memos, emails
- **Reports**: Business reports, research reports
- **Business**: Proposals, business plans
- **Meetings**: Meeting minutes, agendas

## Future Enhancements

- Template versioning
- Custom template creation interface
- Template sharing and collaboration
- Integration with document management systems
- Support for additional file formats (.dotx, .rtf)
