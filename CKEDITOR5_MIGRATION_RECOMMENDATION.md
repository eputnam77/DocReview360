# CKEditor 5 Migration Recommendation

Date: 2026-04-17
Status: Recommended
Owner: Frontend / Product Engineering

## Executive summary

DocReview360 should adopt **CKEditor 5 as the primary rich-text editor for the project review flow**.

This is the recommended path because the current TipTap implementation is carrying too much custom editor behavior in the frontend:

- custom collaboration wiring
- custom tracked changes wiring
- custom comments and inline review behavior
- custom editor lifecycle and persistence code
- custom extension orchestration across many toggles

That complexity is now a direct reliability issue. Recent failures have included:

- audit timeline runtime crashes after approval return
- TipTap editor update loops when opening the editor from the project flow
- repeated regressions in browser-only editor lifecycle paths

CKEditor 5 is the better fit if the product goal is a stable, Word-like review and approval editor with less custom frontend ownership.

TipTap should remain an option, but only in a reduced-risk form:

- use official TipTap capabilities where possible
- remove or disable the highest-risk custom features first
- avoid rebuilding collaboration and tracked changes in app code unless there is a clear product need and a stable vendor-supported path

## Recommendation

### Primary recommendation

Use **CKEditor 5** for the main document editing and review experience in `Projects -> Edit Document`.

### Secondary recommendation

Keep **TipTap** available behind a feature flag or secondary route during migration and for cases where highly customized editing remains necessary.

### Product recommendation

Do **not** carry all current custom editor behaviors forward by default.

Start with a narrower editor contract:

- rich text
- comments
- tracked changes or suggested edits
- revision history
- autosave
- document import/export only where required

Defer these until the core editing path is stable:

- real-time collaboration
- custom Yjs state management
- custom track-change marks
- custom comment mark metadata handling
- optional extension toggles that materially change editor boot order

## Why change

The current frontend problems are not random. They are a structural result of a high-complexity editor path.

The local repo evidence supports that conclusion:

- `frontend/components/TiptapEditorFull.tsx` remains a large orchestration component
- `frontend/lib/useEditorExtensions.ts` coordinates multiple editor features and lifecycle branches
- editor setup currently combines collaboration, tracked changes, comments, templates, validation, autosave, offline draft handling, and custom extension loading

That design increases the chance of:

- render/update loops
- hydration or client-only timing bugs
- extension ordering bugs
- state sync bugs between route state, editor state, and browser storage
- regressions that pass unit tests but fail in the browser

## Option comparison

### Option 1. Adopt CKEditor 5 as the primary editor

Recommendation: **Yes**

Best fit when:

- the product needs review workflows more than deep editor experimentation
- comments, track changes, and revision history should be vendor-supported
- frontend reliability matters more than editor-level flexibility

Advantages:

- official support for collaboration-related review features
- less custom frontend logic for comments and tracked changes
- more standard enterprise document-review model
- lower long-term ownership of editor internals

Costs:

- migration effort is real
- likely license and procurement cost
- data model and content conversion work
- some existing custom editor behaviors may need to be dropped or redesigned

### Option 2. Keep TipTap, but reduce scope and use official plugins

Recommendation: **Possible fallback**

Best fit when:

- vendor cost or procurement blocks CKEditor 5
- the team still wants TipTap's extension model
- the product can accept a narrower feature set in the short term

Required changes:

- disable real-time collaboration by default
- remove custom tracked changes implementation from the main path
- prefer official TipTap capabilities over custom mark/node orchestration
- keep the editor boot path small and deterministic

Advantages:

- lower migration cost than a full editor replacement
- preserves current investment in TipTap content handling
- allows incremental stabilization

Costs:

- team still owns more editor complexity
- official TipTap tracked changes is still not the safest foundation for a mission-critical review workflow
- ongoing brittleness risk remains higher than CKEditor 5

### Option 3. Keep the current custom TipTap path and harden it further

Recommendation: **No**

This is the least attractive option.

Reason:

- it preserves the highest-complexity architecture
- it assumes current instability can be solved purely with patching
- it keeps the team in the business of maintaining custom editor infrastructure

## Recommended target architecture

### Phase 1 target

Use CKEditor 5 for the project document edit flow with a narrow feature set:

- rich text editing
- comments
- tracked changes or suggested edits
- revision history
- autosave
- document load/save integration with existing backend APIs

Disable or defer:

- real-time collaboration
- custom CRDT wiring
- custom inline change-mark extraction
- editor-side feature toggles that change extension load order

### TipTap fallback target

If TipTap remains in use for any route, reduce it to a stable baseline:

- StarterKit and core formatting only
- templates only if they do not mutate editor boot order
- autosave
- validation if isolated from editor initialization

Disable by default:

- collaboration
- custom tracked changes
- custom comment marks
- optional extension toggles with async imports during editor startup

## Features to retire first

These are the first candidates to remove from the primary editing path because they add high lifecycle risk and are the least safe to continue owning in app code:

1. Custom collaboration wiring with Yjs and Hocuspocus provider lifecycle.
2. Custom tracked changes marks and acceptance/rejection flow.
3. Custom inline comment mark metadata extraction.
4. Runtime extension toggles that change the editor's extension graph after boot.
5. Non-essential editor experiments such as optional watermark, advanced structure toggles, or similar boot-path modifiers.

## Migration approach

### Recommended implementation model

Run both editors temporarily.

- CKEditor 5 becomes the new default behind a feature flag.
- TipTap remains available during migration for comparison and rollback.
- One backend document model remains the source of truth.
- Content conversion is explicit and tested.

### Suggested phases

#### Phase 0. Freeze the editor scope

Define the minimum required feature set for the first stable release.

Required:

- edit content
- save content
- comments
- tracked changes or revision history
- submit for review

Not required in phase 0:

- real-time collaboration
- experimental formatting extensions
- editor-specific personalization toggles

#### Phase 1. Build a CKEditor 5 spike

Create a working spike for:

- load document
- edit document
- save document
- open from `Projects -> Edit Document`

Measure:

- browser stability
- bundle impact
- integration effort
- content fidelity

#### Phase 2. Map product features to CKEditor 5

Document each current TipTap feature as one of:

- keep in CKEditor 5
- defer
- drop
- replace with backend-driven workflow

#### Phase 3. Add a dual-editor flag

Add an application setting or feature flag:

- `editor_provider = cke5 | tiptap`

Use it to:

- switch per environment
- run internal user testing
- keep rollback simple

#### Phase 4. Migrate the project edit flow

Move `Projects -> Edit Document` to CKEditor 5 first.

Do not migrate every editor route at once.

This route is the most important because it is also where the current stability issues are most visible.

#### Phase 5. Reduce TipTap surface area

After CKEditor 5 is stable:

- retire TipTap from the primary project edit path
- remove obsolete custom extensions
- keep TipTap only where there is a confirmed need

## Decision matrix

| Criterion | CKEditor 5 | Reduced-scope TipTap | Current custom TipTap |
|---|---|---|---|
| Frontend stability | High | Medium | Low |
| Custom code ownership | Low | Medium | High |
| Track changes readiness | High | Medium to Low | Low |
| Collaboration safety | Medium to High | Medium | Low |
| Migration effort | Medium to High | Medium | Low short-term, high long-term |
| License cost | Higher | Lower | Lower |
| Long-term maintenance risk | Lower | Medium | High |

## Risks

### CKEditor 5 migration risks

- license or procurement delay
- content conversion mismatch between editors
- missing parity for some current custom behavior
- migration work competing with ongoing feature delivery

### TipTap fallback risks

- team may keep too many risky customizations "temporarily"
- official plugin adoption may still leave gaps that trigger more custom work
- product scope may drift back toward the same unstable architecture

## What success looks like

The migration is successful when all of the following are true:

- users can open `Projects -> Edit Document` without frontend crashes
- the editor no longer depends on custom collaboration lifecycle code in the main path
- tracked changes and comments are vendor-supported or clearly simplified
- browser smoke tests cover the full open-edit-save-submit flow
- the old TipTap route is no longer the default editing path

## Immediate next steps

1. Approve CKEditor 5 as the primary migration target.
2. Freeze the first-release editor scope.
3. Create a CKEditor 5 spike for the project edit route.
4. Add a dual-editor feature flag.
5. Disable TipTap collaboration and custom tracked changes by default in the primary path until the replacement is ready.
6. Add a browser regression for `Projects -> Edit Document`.

## Final recommendation

Adopt **CKEditor 5** for the main document review editor.

Keep **TipTap** as a temporary, constrained fallback only.

Do not continue investing in the current custom TipTap collaboration and tracked changes stack as the primary long-term solution.

## Sources

Local repository context:

- `FRONTEND_STABILITY_FINDINGS.md`
- `BRITTLENESS_FINDINGS.md`
- `docs/tiptap-plugins.md`
- `frontend/components/TiptapEditorFull.tsx`
- `frontend/lib/useEditorExtensions.ts`

Official references checked on 2026-04-17:

- CKEditor 5 collaboration overview: https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/collaboration.html
- CKEditor 5 comments: https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/comments/comments.html
- CKEditor 5 track changes: https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/track-changes/track-changes.html
- CKEditor 5 track changes integration: https://ckeditor.com/docs/ckeditor5/latest/features/collaboration/track-changes/track-changes-integration.html
- Tiptap collaboration overview: https://tiptap.dev/docs/collaboration/getting-started/overview
- Tiptap tracked changes overview: https://tiptap.dev/docs/tracked-changes/getting-started/overview
- Lexical overview: https://lexical.dev/
- Slate collaboration walkthrough: https://docs.slatejs.org/walkthroughs/07-enabling-collaborative-editing
