# Approval-Based Project Assignments

## Overview

DocReview360 now supports comprehensive project assignment tracking that includes not only direct project assignments but also assignments through the approval workflow system.

## How "Projects Assigned to Me" Works

When a user visits the "Projects Assigned to Me" page (`/projects`), the system now considers projects where the user is assigned through **any** of these mechanisms:

### 1. Direct Project Assignment
- User is set as `project.user` (primary project owner)
- User is set as `project.temp_user` (temporary assignment)

### 2. Approval Workflow Assignment
- User is assigned as a **reviewer** in any approval step for the project's workflow
- This includes all approval roles:
  - **SME** (Subject Matter Expert)
  - **FLM** (Front Line Manager) 
  - **PPM** (Product Policy Manager)
  - **TW** (Technical Writer)
  - **Senior TW** (Senior Technical Writer)
  - **TW Manager** (Technical Writing Manager)
  - **Attorney** (Legal Review)

## Implementation Details

### Backend Changes

The `list_projects()` function in `src/docreview360/search.py` has been enhanced to:

1. **Check direct assignments** (existing functionality)
2. **Check approval assignments** (new functionality)
   - For projects with workflows, query all approvals
   - Include project if user is listed as any reviewer

```python
def list_projects(user: str | None = None) -> list[ProjectModel]:
    """Return projects optionally filtered by assigned user.
    
    Includes projects where the user is:
    1. Directly assigned as project.user
    2. Temporarily assigned as project.temp_user  
    3. Assigned as a reviewer in any approval step
    """
    from .approvals import list_approvals
    
    with project_lock:
        result = []
        for proj in projects.values():
            _expire_temp_assignment(proj, lock_held=True)
            
            # Check direct assignments
            if user is None or proj.user == user or proj.temp_user == user:
                result.append(proj)
                continue
                
            # Check approval assignments if user is specified and project has workflow
            if user and proj.workflow:
                # Get all approvals for this project's workflow
                workflow_approvals = list_approvals(proj.workflow)
                # Check if user is assigned as a reviewer in any approval
                for approval in workflow_approvals:
                    if approval.reviewer == user:
                        result.append(proj)
                        break
                        
        return result
```

### API Endpoints

#### Enhanced `/projects` Endpoint
- **GET** `/projects?user={username}` or with `X-User` header
- Now includes approval-based assignments
- Maintains backward compatibility

#### New `/projects/assigned/{username}` Endpoint  
- **GET** `/projects/assigned/{username}`
- Debug endpoint to see all projects assigned to a specific user
- Useful for testing and verification

## Testing

Use the test script `test_approval_assignments.py` to verify the functionality:

```bash
python test_approval_assignments.py
```

This script:
1. Creates a test project with automatic approval assignments
2. Verifies that all assigned reviewers can see the project
3. Confirms that unrelated users cannot see the project
4. Provides detailed test results

## Example Workflow

1. **Project Creation**: When a project is created with a workflow, automatic approval steps are generated
2. **Approval Assignment**: Each approval step gets a default reviewer (SME, FLM, PPM, etc.)
3. **User Visibility**: All assigned reviewers now see the project in their "Projects Assigned to Me" list
4. **Workflow Progression**: As approvals are completed, the project moves through the workflow phases

## Benefits

- **Comprehensive Assignment Tracking**: Users see all projects they're responsible for
- **Workflow Integration**: Approval assignments are automatically considered
- **Role-Based Visibility**: Different approval roles (SME, FLM, etc.) all see relevant projects
- **Backward Compatibility**: Existing direct assignments continue to work
- **Performance Optimized**: Uses existing caching mechanisms

## Future Enhancements

Potential improvements could include:
- **Assignment Types**: Distinguish between direct vs. approval assignments in the UI
- **Role Filtering**: Allow filtering by specific approval roles
- **Assignment History**: Track when and how assignments were made
- **Notification Integration**: Alert users when they're assigned to new projects

---

## Reviewer Sign-off vs. Formal Approval — Clarification

DocReview360 has **two distinct acknowledgment mechanisms** that serve different purposes.
Understanding the difference is critical for compliance and audit purposes.

### Reviewer Sign-off (Concurrence)

**Location:** Assignments section of the project page (`/projects/{id}` — Assignments tab).

**What it is:** An informal, in-system acknowledgment that a reviewer has read the document
and either concurred, non-concurred, or acknowledged receipt. This is part of the iterative
review lifecycle and may happen multiple times across review rounds.

**Properties:**
- Recorded in the review assignment audit trail (`/projects/{id}/assignments`).
- Does **not** require a cryptographic signature or external signature provider.
- Status values: `pending`, `in_progress`, `signed` (concurred), `non_concurred`, `declined`.
- A reviewer may be invited to review without ever appearing in the Approvals table.
- Multiple sign-offs per phase are normal; each reviewer who has an assignment can sign off.

**When to use:** Use assignments/sign-off for the document review and comment-resolution
cycle — i.e., to track that everyone who needs to read the document has done so and noted
their position.

### Formal Approval

**Location:** Approvals section of the project page (`/projects/{id}` — Approvals tab).

**What it is:** A legally binding approval record created using a configured signature method.
Formal approvals are tied to a specific document version and phase; they are cryptographically
linked to the document content hash at time of signing.

**Properties:**
- Requires an explicit approval row to be created for a reviewer (owner/admin action).
- Signature method is one of: **Documenso**, **DocuSign**, or **in-app initials**.
- Recorded via `POST /approvals/{id}/sign` (new endpoint, RELEASE_CHECKLIST §51).
- Status values: `pending`, `approved`, `overdue`, `rejected`.
- Once approved, the record is **immutable** (cannot be reset without admin action and
  creates an audit entry).
- All required approvals must be `approved` before a phase can be advanced.

**When to use:** Use formal approvals when a phase gate requires documented, auditable,
legally binding sign-off — e.g., senior management, legal, or regulatory approval before
release or publication.

### Summary Table

| Aspect | Reviewer Sign-off | Formal Approval |
|---|---|---|
| **UI location** | Assignments section | Approvals section |
| **Binding** | Informal / acknowledgment | Legal record |
| **Signature** | None required | Documenso / DocuSign / initials |
| **Document hash** | Not linked | Cryptographically linked |
| **Phase gate** | No | Yes (blocks advance if required) |
| **Immutable** | No (can be reset) | Yes (admin reset only) |
| **Audit trail** | Assignment log | Approval + audit log |
| **Who can do it** | Any invited reviewer | Only assigned approvers |

### API Endpoints

| Action | Endpoint |
|---|---|
| Sign off (concur) | `POST /projects/{id}/assignments/{aid}/sign` |
| Non-concur | `POST /projects/{id}/assignments/{aid}/non-concur` |
| Formally approve | `POST /approvals/{id}/sign` |
| Sign with initials | `POST /approvals/{id}/sign-initials` |
| View approval history | `GET /approvals/{id}/history` |