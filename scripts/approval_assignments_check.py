#!/usr/bin/env python3
"""
Test script to verify that projects are correctly assigned to users through approvals.
This tests the enhanced list_projects function that includes approval assignments.
"""

import requests

API_BASE = "http://localhost:8000"


def test_approval_assignments():
    """Test that users can see projects where they are assigned as reviewers."""

    print("🧪 Testing Approval-Based Project Assignments")
    print("=" * 50)

    # 1. Create a test project with workflow
    print("\n1. Creating test project...")
    project_data = {
        "name": "Test Approval Assignment Project",
        "document_number": "TEST-APPROVAL-001",
        "user": "project_owner",  # Direct project owner
        "phase": "Public Comment / Proposed Rulemaking",
        "workflow": "Public Comment / Proposed Rulemaking",
    }

    response = requests.post(f"{API_BASE}/projects", json=project_data)
    if response.status_code != 201:
        print(f"❌ Failed to create project: {response.text}")
        return False

    project = response.json()
    project_id = project["id"]
    workflow_id = project["workflow"]
    print(f"✅ Created project: {project_id}")
    print(f"   Workflow: {workflow_id}")

    # 2. Check what approvals were automatically created
    print("\n2. Checking automatic approvals...")
    approvals_response = requests.get(f"{API_BASE}/approvals?workflow={workflow_id}")
    if approvals_response.status_code != 200:
        print(f"❌ Failed to get approvals: {approvals_response.text}")
        return False

    approvals = approvals_response.json()
    print(f"✅ Found {len(approvals)} automatic approvals:")
    for approval in approvals:
        print(f"   - {approval['reviewer']}: {approval['description']}")

    # 3. Test that project owner sees the project
    print("\n3. Testing project owner assignment...")
    owner_projects = requests.get(f"{API_BASE}/projects/assigned/project_owner")
    if owner_projects.status_code != 200:
        print(f"❌ Failed to get owner projects: {owner_projects.text}")
        return False

    owner_project_list = owner_projects.json()
    owner_has_project = any(p["id"] == project_id for p in owner_project_list)
    print(f"✅ Project owner sees {len(owner_project_list)} projects")
    print(f"   Has test project: {owner_has_project}")

    # 4. Test that SME reviewer sees the project
    print("\n4. Testing SME reviewer assignment...")
    sme_projects = requests.get(f"{API_BASE}/projects/assigned/SME")
    if sme_projects.status_code != 200:
        print(f"❌ Failed to get SME projects: {sme_projects.text}")
        return False

    sme_project_list = sme_projects.json()
    sme_has_project = any(p["id"] == project_id for p in sme_project_list)
    print(f"✅ SME reviewer sees {len(sme_project_list)} projects")
    print(f"   Has test project: {sme_has_project}")

    # 5. Test that FLM reviewer sees the project
    print("\n5. Testing FLM reviewer assignment...")
    flm_projects = requests.get(f"{API_BASE}/projects/assigned/Front Line Manager")
    if flm_projects.status_code != 200:
        print(f"❌ Failed to get FLM projects: {flm_projects.text}")
        return False

    flm_project_list = flm_projects.json()
    flm_has_project = any(p["id"] == project_id for p in flm_project_list)
    print(f"✅ FLM reviewer sees {len(flm_project_list)} projects")
    print(f"   Has test project: {flm_has_project}")

    # 6. Test that unrelated user doesn't see the project
    print("\n6. Testing unrelated user...")
    unrelated_projects = requests.get(f"{API_BASE}/projects/assigned/unrelated_user")
    if unrelated_projects.status_code != 200:
        print(f"❌ Failed to get unrelated user projects: {unrelated_projects.text}")
        return False

    unrelated_project_list = unrelated_projects.json()
    unrelated_has_project = any(p["id"] == project_id for p in unrelated_project_list)
    print(f"✅ Unrelated user sees {len(unrelated_project_list)} projects")
    print(f"   Has test project: {unrelated_has_project} (should be False)")

    # 7. Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY:")
    print(f"   Project Owner Assignment: {'✅ PASS' if owner_has_project else '❌ FAIL'}")
    print(f"   SME Reviewer Assignment: {'✅ PASS' if sme_has_project else '❌ FAIL'}")
    print(f"   FLM Reviewer Assignment: {'✅ PASS' if flm_has_project else '❌ FAIL'}")
    print(f"   Unrelated User Exclusion: {'✅ PASS' if not unrelated_has_project else '❌ FAIL'}")

    all_passed = (
        owner_has_project and sme_has_project and flm_has_project and not unrelated_has_project
    )
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")

    return all_passed


if __name__ == "__main__":
    try:
        success = test_approval_assignments()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        exit(1)
