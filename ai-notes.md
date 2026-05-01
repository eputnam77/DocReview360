# Update requests
When you complete a task, mark the item as done ("X") in the square brackets.


- [ ] I want to add Oxygen XML Web Author as a document editor option along with the others. Currently in Configurations > Integrations, we list XML, so Oxygen XML Web Author would work.
- [ ] In Configuration > Integrations, for Signature Provider and Fallback Signature Provider, I thought we also had Documenso, DocuSign, Initials. I thought those were in this dropdown previously. Also, what is Local?
- [ ] In Tools > Converter, I tried it and got "WARNING:docreview360.document_converter:PDF output is not yet supported; returning plain text instead". Also there are only two options to convert: PDF and HTML

- [ ] "In Configuration > Workflows, update core workflow set and add descriptions.
| Workflow                                 | Purpose                                                                                                                                                               |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `standard-document-review`               | Default review path for most documents before publication. Includes technical, editorial, manager, legal/policy, approval, and publication-readiness steps as needed. |
| `pre-coordination-review`                | Informal early review to resolve major issues before formal coordination begins.                                                                                      |
| `fast-track-review`                      | Expedited path with fewer reviewers, shorter due dates, and documented justification.                                                                                 |
| `single-branch-coordination`             | Review path limited to one branch or office.                                                                                                                          |
| `multi-branch-coordination`              | Review path requiring multiple branches, offices, or specialties.                                                                                                     |
| `external-coordination`                  | Review path involving outside organizations or external partners.                                                                                                     |
| `requirements-intake-review`             | Used when the main work is collecting inputs, requirements, data, or source material before review can begin.                                                         |
| `publication-readiness-and-distribution` | Final publication package, distribution, archive, and notification workflow.                                                                                          |
| `post-publication-implementation`        | Tracks follow-up after publication.                                                                                                                                   |"

- [ ] "In Configuration > Document Types, I get this error:
A <Select.Item /> must have a value prop that is not an empty string. This is because the Select value can be set to an empty string to clear the selection and show the placeholder."

- [ ] I created a new project, and before I even created a document, the Document Quality Score was 65% quality. This can show the average for policy memos (the document type I selected for my project), but it shouldn't give me a quality score even before I begin creating a document
- [ ] I created a new project and I would think that the Audit History would show project created or similar. It currently doesn't
- [ ] I like how Project Details shows "Project Details (collapsed)" when that section is collapsed. Let's add the same "(collapsed)" to "Approvals, Review Sign-off & Concurrence", "Comments", and Records Retention (NARA)" sections. All sections should be collapsed by default
- [ ] I created a new project and selected the Final Issuance phase with the fast-track-coordination workflow. Even though I just created the project, it's already showing Status of Complete and Overall Progress of 90% complete. I just created this project--and haven't even created a new document--so we're 0% complete.
- [ ] CKEditor5 should be the default editor when I click Edit Document from Projects page, not the TipTap backup. Currently, when I click Edit document, it opens in TipTap
- [ ] For TipTap, we must use ONLY TipTap plugins, but for formatting, I need Headings 1-3, Bold, italics, bulleted list, nnumbered list, indents. Also, rather than having buttons that say the full names ("Bold", "Italic", etc.), is there a shorthand TipTap pluging ("B" for bold, "i" for italics, etc.)?
- [ ] In document editors, when i click edit document, confirm that it uses the default template for the document type and doc editor by default. I don't see an option to select a template, but we also shouldn't need to do that. Once we select the document type and know the doc editor, it should give us the correct template to use
- [ ] In Doc editor, CKEditor5, I typed some words and tried to select headings 1-3, and none worked. Confirm that the heading dropdown formatting works. Note that when I click the B for bold, I for italics, and u for underdline, those work. Bulleted list and numbnered lists do NOT work.
- [ ] In Project/[id]/index, within Project Details, there's a card with: ID, #, Type, Title, Owner, Status, and Updated. For all projects, # shows as "12". I don't know what this is. This should be the "Document Number" that we select when we create the project (and can be updated if need through Edit Project). See where this “12” came from and ensure that “#” shows “Document Number” and the actual document number.















































