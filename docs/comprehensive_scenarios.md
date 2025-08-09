# Comprehensive End-to-End Testing Scenarios

The following scenarios provide comprehensive coverage of DocReview360's functionality, including project creation, workflow management, approval processes, reviewer assignments, Documenso integration, comment systems, and status tracking.

## Table of Contents

### Project Creation & Initial Assignment Scenarios
- [Scenario 1: Basic Project Creation with Direct Assignment](#scenario-1-basic-project-creation-with-direct-assignment)
- [Scenario 2: Project Creation with Workflow Auto-Assignment](#scenario-2-project-creation-with-workflow-auto-assignment)
- [Scenario 3: Temporary Assignment Management](#scenario-3-temporary-assignment-management)

### Document Management & Content Scenarios
- [Scenario 4: Document Import and Content Management](#scenario-4-document-import-and-content-management)
- [Scenario 5: Multi-Document Project Workflow](#scenario-5-multi-document-project-workflow)

### Approval & Workflow Progression Scenarios
- [Scenario 6: Complete Linear Approval Workflow](#scenario-6-complete-linear-approval-workflow)
- [Scenario 7: Parallel Review Workflow](#scenario-7-parallel-review-workflow)
- [Scenario 8: Approval Rejection and Workflow Reset](#scenario-8-approval-rejection-and-workflow-reset)

### Documenso Integration Scenarios
- [Scenario 9: Digital Signature Integration](#scenario-9-digital-signature-integration)
- [Scenario 10: Signature with Return URL Integration](#scenario-10-signature-with-return-url-integration)
- [Scenario 11: Bulk Signature Management](#scenario-11-bulk-signature-management)

### Comment & Review Scenarios
- [Scenario 12: Collaborative Commenting Workflow](#scenario-12-collaborative-commenting-workflow)
- [Scenario 13: Review Comments with Approval Integration](#scenario-13-review-comments-with-approval-integration)

### Search & Discovery Scenarios
- [Scenario 14: Comprehensive Search Testing](#scenario-14-comprehensive-search-testing)
- [Scenario 15: Advanced Search with Workflow State](#scenario-15-advanced-search-with-workflow-state)

### User Management & Assignment Scenarios
- [Scenario 16: Role-Based Assignment Testing](#scenario-16-role-based-assignment-testing)
- [Scenario 17: Cross-Organizational Workflow](#scenario-17-cross-organizational-workflow)

### Performance & Edge Case Scenarios
- [Scenario 18: High-Volume Project Management](#scenario-18-high-volume-project-management)
- [Scenario 19: Concurrent User Scenarios](#scenario-19-concurrent-user-scenarios)
- [Scenario 20: Error Handling and Recovery](#scenario-20-error-handling-and-recovery)

### Integration & API Scenarios
- [Scenario 21: Full API Workflow Coverage](#scenario-21-full-api-workflow-coverage)
- [Scenario 22: Frontend-Backend Integration](#scenario-22-frontend-backend-integration)

### Additional Advanced Scenarios
- [Scenario 23: SME Reassignment Mid-Workflow](#scenario-23-sme-reassignment-mid-workflow)
- [Scenario 24: Multi-Phase Workflow with Phase-Specific Comments](#scenario-24-multi-phase-workflow-with-phase-specific-comments)
- [Scenario 25: Archive and Audit Trail Verification](#scenario-25-archive-and-audit-trail-verification)
- [Scenario 26: Document Number Change Mid-Workflow](#scenario-26-document-number-change-mid-workflow)
- [Scenario 27: Document Type Change with Workflow Continuity](#scenario-27-document-type-change-with-workflow-continuity)

### Reference Sections
- [Quick Reference Summary](#quick-reference-summary)

## Project Creation & Initial Assignment Scenarios

### Scenario 1: Basic Project Creation with Direct Assignment
**Objective**: Test basic project creation and direct user assignment
**Steps**:
1. Create a project using `POST /projects` with direct user assignment
2. Verify the project appears in assigned user's project list via `GET /projects/assigned/{username}`
3. Verify project status is set to "Draft" initially
4. Confirm project metadata (name, document_number, priority) is correctly stored
5. Test project search functionality to find the newly created project

**Expected Outcomes**:
- Project created successfully with unique ID
- Direct assignment works correctly
- Project visible in user's assigned projects
- Search returns the project in results

### Scenario 2: Project Creation with Workflow Auto-Assignment
**Objective**: Test automatic approval assignments when creating projects with workflows
**Steps**:
1. Create a project with workflow using `POST /projects` with phase="Public Comment"
2. Verify automatic workflow creation via `GET /workflows/{workflow_id}`
3. Check that automatic approvals are created for all roles (SME, FLM, PPM, TW, Senior TW, TW Manager)
4. Verify each assigned reviewer can see the project in their assignments
5. Confirm unrelated users cannot see the project

**Expected Outcomes**:
- Workflow automatically created with proper phase
- 6 approval records created for standard roles
- All approval reviewers can see project in their assignments
- Project status reflects workflow phase

### Scenario 3: Temporary Assignment Management
**Objective**: Test temporary user assignments with expiration
**Steps**:
1. Create a project with primary user assignment
2. Assign temporary user using assignment API with expiration date
3. Verify both primary and temporary users see the project
4. Wait for or simulate expiration time passing
5. Verify temporary assignment is automatically removed
6. Confirm only primary user sees the project after expiration

**Expected Outcomes**:
- Temporary assignments work correctly
- Both users see project during temporary period
- Automatic cleanup of expired assignments
- Primary assignment persists after temp expiration

## Document Management & Content Scenarios

### Scenario 4: Document Import and Content Management
**Objective**: Test document import, editing, and version management
**Steps**:
1. Import a document using `POST /documents/import` (Markdown, DOCX, PDF)
2. Edit document content using `PUT /documents/{doc_id}`
3. Create document versions and track changes
4. Link document to a project
5. Export document in different formats (HTML, PDF, DOCX)
6. Test document search functionality

**Expected Outcomes**:
- Documents import successfully from various formats
- Content editing persists correctly
- Version history is maintained
- Project linkage works
- Export functionality produces correct outputs

### Scenario 5: Multi-Document Project Workflow
**Objective**: Test projects with multiple documents and complex workflows
**Steps**:
1. Create a project with multiple document types
2. Import different document formats (templates, references, drafts)
3. Start a complex workflow (parallel SME review)
4. Track document progression through workflow phases
5. Test document consolidation and final output generation

**Expected Outcomes**:
- Multiple documents can be managed in single project
- Complex workflows handle multiple documents correctly
- Document relationships are maintained
- Final consolidation works properly

## Approval & Workflow Progression Scenarios

### Scenario 6: Complete Linear Approval Workflow
**Objective**: Test full approval workflow from start to completion
**Steps**:
1. Create project with "branch-coordination" workflow
2. Verify automatic assignment of all 6 approval roles
3. Process approvals in sequence: SME → FLM → PPM → TW → Senior TW → TW Manager
4. For each approval:
   - Reviewer accesses their assigned projects
   - Reviews document content
   - Updates approval state using `PUT /approvals/{approval_id}`
   - Adds digital signature placeholder
5. Verify workflow advances after each approval
6. Confirm project completion when all approvals are done

**Expected Outcomes**:
- Sequential approval process works correctly
- Workflow phase advances appropriately
- Project status updates reflect approval progress
- All approvals required for completion
- Audit trail maintained for all approval actions

### Scenario 7: Parallel Review Workflow
**Objective**: Test workflows with parallel approval steps
**Steps**:
1. Create project with parallel SME workflow
2. Assign multiple SMEs for concurrent review
3. Process parallel approvals simultaneously
4. Test workflow advancement logic when all parallel approvals complete
5. Verify subsequent sequential approvals work after parallel phase

**Expected Outcomes**:
- Multiple parallel approvals can be processed
- Workflow waits for all parallel approvals
- Correct advancement after parallel phase completion
- No conflicts between parallel reviewers

### Scenario 8: Approval Rejection and Workflow Reset
**Objective**: Test rejection handling and workflow reset scenarios
**Steps**:
1. Create project and start approval workflow
2. Process initial approvals successfully
3. Have a mid-workflow reviewer reject the approval
4. Test workflow reset/revision process
5. Restart approval process from appropriate point
6. Complete workflow after addressing rejection comments

**Expected Outcomes**:
- Rejection properly stops workflow progression
- Reset mechanism works correctly
- Revision tracking is maintained
- Restarted workflow functions properly

## Documenso Integration Scenarios

### Scenario 9: Digital Signature Integration
**Objective**: Test Documenso signature request and completion flow
**Steps**:
1. Create project requiring digital signatures
2. Generate signature request using `request_signature()`
3. Simulate signature completion via `complete_signature()`
4. Verify signature status updates via `signature_status()`
5. Test webhook processing for signature events
6. Confirm approval state updates when signature is completed

**Expected Outcomes**:
- Signature requests generated correctly
- Signature URLs accessible and functional
- Completion updates approval status
- Webhook processing works properly
- Audit trail includes signature events

### Scenario 10: Signature with Return URL Integration
**Objective**: Test signature requests with return URL functionality
**Steps**:
1. Create approval requiring signature with return URL
2. Generate signature request with return URL and approval ID
3. Simulate signature completion with return navigation
4. Verify approval auto-updates on signature completion
5. Test error handling for failed signature requests

**Expected Outcomes**:
- Return URLs properly embedded in signature requests
- Navigation back to system works correctly
- Auto-approval updates function
- Error handling prevents system corruption

### Scenario 11: Bulk Signature Management
**Objective**: Test multiple signature requests for single workflow
**Steps**:
1. Create project requiring multiple signatures (different roles)
2. Generate signature requests for multiple reviewers
3. Process signatures in various orders (sequential, random)
4. Verify workflow completion requires all signatures
5. Test signature status tracking across multiple requests

**Expected Outcomes**:
- Multiple signature requests managed correctly
- Order independence for signature completion
- Proper workflow completion logic
- Status tracking accurate across all signatures

## Comment & Review Scenarios

### Scenario 12: Collaborative Commenting Workflow
**Objective**: Test comment system integration with approval workflow
**Steps**:
1. Create project and start review workflow
2. Add comments from different reviewers using `POST /comments`
3. Test threaded comments (replies to comments)
4. Include @mentions in comments and verify notification logic
5. Use emoji support in comments
6. Track comment history throughout workflow progression

**Expected Outcomes**:
- Comments associated correctly with documents
- Threaded commenting works properly
- @mention extraction and processing functions
- Emoji replacement works correctly
- Comment history preserved through workflow

### Scenario 13: Review Comments with Approval Integration
**Objective**: Test comments influencing approval decisions
**Steps**:
1. Start approval workflow with comment requirements
2. Add review comments before approval decisions
3. Test conditional approvals based on comment content
4. Verify comment resolution tracking
5. Test approval state changes based on comment threading

**Expected Outcomes**:
- Comments properly linked to approval decisions
- Comment resolution workflow functions
- Approval conditions based on comments work
- History tracking includes comment context

## Search & Discovery Scenarios

### Scenario 14: Comprehensive Search Testing
**Objective**: Test all search functionality across projects and documents
**Steps**:
1. Create multiple projects with varied content and metadata
2. Test basic text search across project names and descriptions
3. Test document content search functionality
4. Use saved search feature for repeated queries
5. Test search filtering by user, project type, status
6. Verify search result ranking and relevance

**Expected Outcomes**:
- Search returns relevant results across all content types
- Filtering works correctly for all criteria
- Saved searches persist and can be reused
- Search performance is acceptable
- Result ranking reflects relevance appropriately

### Scenario 15: Advanced Search with Workflow State
**Objective**: Test search functionality considering workflow states
**Steps**:
1. Create projects in various workflow phases
2. Search for projects by approval status
3. Filter search results by workflow phase
4. Test search for projects assigned to specific reviewers
5. Search for overdue approvals and projects

**Expected Outcomes**:
- Workflow-aware search functions correctly
- Status-based filtering works properly
- Reviewer-based searches return correct results
- Time-based queries work for overdue items

## User Management & Assignment Scenarios

### Scenario 16: Role-Based Assignment Testing
**Objective**: Test assignment and visibility based on user roles
**Steps**:
1. Create users with different roles (SME, FLM, PPM, TW, etc.)
2. Create projects and verify role-based auto-assignment
3. Test role-based project visibility
4. Verify role-specific workflow permissions
5. Test role changes and assignment updates

**Expected Outcomes**:
- Role-based assignments work correctly
- Visibility respects role permissions
- Workflow permissions enforced properly
- Role changes update assignments appropriately

### Scenario 17: Cross-Organizational Workflow
**Objective**: Test workflows spanning multiple organizations
**Steps**:
1. Create users from different organizations
2. Create projects requiring cross-org approvals
3. Test assignment and visibility across org boundaries
4. Verify approval permissions and restrictions
5. Test project completion across organizations

**Expected Outcomes**:
- Cross-org assignments function correctly
- Proper security boundaries maintained
- Approvals work across organizations
- Project completion logic handles multiple orgs

## Performance & Edge Case Scenarios

### Scenario 18: High-Volume Project Management
**Objective**: Test system performance with many projects and approvals
**Steps**:
1. Create large number of projects (100+)
2. Generate multiple workflows with many approvals
3. Test search performance with large datasets
4. Verify assignment queries perform well at scale
5. Test bulk operations and batch processing

**Expected Outcomes**:
- System performance remains acceptable at scale
- Search functionality works efficiently
- Assignment queries scale properly
- Bulk operations complete successfully

### Scenario 19: Concurrent User Scenarios
**Objective**: Test system behavior with multiple concurrent users
**Steps**:
1. Simulate multiple users accessing system simultaneously
2. Test concurrent project creation and assignment
3. Test concurrent approval processing
4. Verify comment system with multiple simultaneous users
5. Test workflow advancement with concurrent approvals

**Expected Outcomes**:
- No data corruption with concurrent access
- Proper locking and synchronization
- Consistent state across concurrent operations
- No race conditions in workflow advancement

### Scenario 20: Error Handling and Recovery
**Objective**: Test system resilience and error handling
**Steps**:
1. Test invalid input handling for all API endpoints
2. Simulate network failures during Documenso integration
3. Test system behavior with corrupted workflow states
4. Verify graceful degradation when external services fail
5. Test system recovery after temporary failures

**Expected Outcomes**:
- Proper error messages for invalid inputs
- Graceful handling of external service failures
- System state remains consistent during errors
- Recovery mechanisms work correctly
- No data loss during error conditions

## Integration & API Scenarios

### Scenario 21: Full API Workflow Coverage
**Objective**: Test all API endpoints in realistic workflow combinations
**Steps**:
1. Use API to create complete project workflow
2. Test all CRUD operations for projects, documents, approvals
3. Verify API response consistency and error handling
4. Test API authentication and authorization
5. Validate API documentation against actual behavior

**Expected Outcomes**:
- All API endpoints function as documented
- Consistent response formats across endpoints
- Proper error handling and status codes
- Authentication/authorization works correctly
- API documentation is accurate and complete

### Scenario 22: Frontend-Backend Integration
**Objective**: Test complete frontend-backend integration workflows
**Steps**:
1. Test project creation through frontend interface
2. Verify workflow management through UI
3. Test approval processing via frontend
4. Verify comment system integration
5. Test search functionality through UI

**Expected Outcomes**:
- Frontend properly communicates with backend
- UI state reflects backend data correctly
- All user interactions work as expected
- Error handling works through UI
- Data consistency maintained across interface

## Additional Advanced Scenarios

### Scenario 23: SME Reassignment Mid-Workflow
**Objective**: Test reassigning Subject Matter Experts during active workflows
**Steps**:
1. Create project and assign initial SME reviewer
2. Start approval workflow and get to SME review stage
3. Reassign to different SME using reviewer assignment API
4. Verify new SME can see project and old SME cannot
5. Complete approval with new SME
6. Verify workflow continues correctly

**Expected Outcomes**:
- SME reassignment works seamlessly
- Project visibility updates immediately
- Workflow state remains consistent
- Audit trail tracks reassignment

### Scenario 24: Multi-Phase Workflow with Phase-Specific Comments
**Objective**: Test complex workflows with different approval requirements per phase
**Steps**:
1. Create project with multi-phase workflow (Draft → Review → Public Comment → Final)
2. Progress through each phase with different reviewer sets
3. Add phase-specific comments and requirements
4. Test phase advancement and requirement validation
5. Verify final approval only after all phases complete

**Expected Outcomes**:
- Phase-specific approvals work correctly
- Comments are associated with correct phases
- Phase advancement logic functions properly
- All phases required for final completion

### Scenario 25: Archive and Audit Trail Verification
**Objective**: Test document archival and complete audit trail functionality
**Steps**:
1. Complete full project workflow with all approvals
2. Archive completed project using archive functionality
3. Verify audit trail captures all actions (creation, assignments, approvals, comments)
4. Test audit trail search and filtering
5. Verify archived project accessibility and immutability

**Expected Outcomes**:
- Archive process works correctly
- Complete audit trail maintained
- Audit trail search functionality works
- Archived projects remain accessible but immutable

### Scenario 26: Document Number Change Mid-Workflow
**Objective**: Test changing document number while maintaining document ID and workflow integrity
**Steps**:
1. Create project with initial document number (e.g., "AC-001")
2. Start approval workflow and progress to SME review stage
3. SME updates document number to new value (e.g., "AC-001-Rev1") via `PUT /projects/{project_id}`
4. Verify document ID remains unchanged throughout the process
5. Verify workflow continues with updated document number
6. Check that all approval assignments and signatures remain valid
7. Verify audit trail captures document number change
8. Complete workflow and verify final project has updated document number

**Expected Outcomes**:
- Document ID remains immutable throughout the process
- Document number updates successfully via API
- Workflow integrity maintained after number change
- All approval assignments remain valid
- Audit trail properly records the document number change
- Search functionality works with both old and new document numbers
- Project completion works with updated document number

**Current Status**: ⚠️ **MISSING FUNCTIONALITY** - The `update_project` function currently does NOT support `document_number` updates

### Scenario 27: Document Type Change with Workflow Continuity
**Objective**: Test changing document type (e.g., Advisory Circular to Policy Statement) while preserving workflow
**Steps**:
1. Create project with document type "Advisory Circular" and start workflow
2. Progress workflow to mid-point (e.g., FLM approval stage)
3. Update document type to "Policy Statement" via `PUT /projects/{project_id}`
4. Verify document ID remains unchanged
5. Verify existing approvals and signatures remain valid
6. Check that workflow continues with updated document type
7. Verify approval assignments still work for remaining reviewers
8. Complete workflow and verify final project has updated document type
9. Test search functionality with both old and new document types
10. Verify reporting and dashboard reflect the document type change

**Expected Outcomes**:
- Document ID remains immutable throughout the process
- Document type updates successfully while preserving workflow state
- Existing approvals and digital signatures remain valid
- Remaining approval steps continue normally
- Project assignment visibility works with new document type
- Search indexes are updated for both old and new types
- Audit trail captures document type change with timestamp
- Reporting and dashboards reflect the updated document type

**Current Status**: ✅ **FUNCTIONALITY EXISTS** - Document type changes are supported and tested in `test_name_change_propagation.py`

## Quick Reference Summary

### Core Entity Workflows:
- **Projects**: Creation, assignment, search, priority management
- **Documents**: Import, edit, version control, export, archive
- **Workflows**: Creation, phase progression, approval routing
- **Approvals**: Assignment, processing, digital signatures, state management
- **Comments**: Creation, threading, mentions, emoji support
- **Users**: Role-based access, cross-org assignments, temporary assignments

### Key Integration Points:
- **Documenso**: Signature requests, completion webhooks, status tracking
- **Search**: Full-text indexing, saved searches, filter capabilities
- **Frontend**: UI consistency, error handling, real-time updates
- **API**: Complete CRUD operations, authentication, documentation

### Critical Test Areas:
- **Concurrency**: Multiple users, simultaneous operations, data consistency
- **Performance**: Large datasets, search efficiency, bulk operations
- **Security**: Access control, cross-org boundaries, audit trails
- **Error Handling**: Network failures, invalid inputs, graceful degradation

These scenarios provide comprehensive coverage of all major DocReview360 functionality and should be used to ensure thorough testing of the system's end-to-end capabilities.
