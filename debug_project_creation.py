#!/usr/bin/env python3
"""
Diagnostic script to test project creation and identify issues.
Run this script to test the project creation functionality.
"""

import json
import requests
import sys
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"
TEST_PROJECT = {
    "id": f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
    "name": "Test Project for Debugging",
    "user": "test_user",
    "doc_type": "Test Document",
    "phase": "Test Phase",
    "workflow": "Test Workflow",
    "description": "This is a test project to debug creation issues"
}

def test_api_health():
    """Test if the API is running and healthy."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"✅ API Health Check: {response.status_code}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ API Health Check Failed: {e}")
        return False

def test_project_creation():
    """Test creating a new project."""
    try:
        print(f"\n🔄 Creating test project: {TEST_PROJECT['id']}")
        response = requests.post(
            f"{API_BASE}/projects",
            json=TEST_PROJECT,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"📊 Creation Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")

        if response.status_code == 201:
            project_data = response.json()
            print(f"✅ Project Created Successfully:")
            print(f"   ID: {project_data.get('id')}")
            print(f"   Name: {project_data.get('name')}")
            print(f"   User: {project_data.get('user')}")
            return project_data.get('id')
        else:
            print(f"❌ Project Creation Failed:")
            print(f"   Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ Project Creation Error: {e}")
        return None

def test_project_retrieval(project_id: str) -> bool:
    """Test retrieving the created project."""
    try:
        print(f"\n🔄 Retrieving project: {project_id}")
        response = requests.get(f"{API_BASE}/projects/{project_id}", timeout=5)

        print(f"📊 Retrieval Response Status: {response.status_code}")

        if response.status_code == 200:
            project_data = response.json()
            print(f"✅ Project Retrieved Successfully:")
            print(f"   ID: {project_data.get('id')}")
            print(f"   Name: {project_data.get('name')}")
            return True
        else:
            print(f"❌ Project Retrieval Failed: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Project Retrieval Error: {e}")
        return False

def test_project_list():
    """Test listing all projects."""
    try:
        print(f"\n🔄 Listing all projects")
        response = requests.get(f"{API_BASE}/projects", timeout=5)

        print(f"📊 List Response Status: {response.status_code}")

        if response.status_code == 200:
            projects = response.json()
            print(f"✅ Found {len(projects)} projects:")
            for i, project in enumerate(projects, 1):
                print(f"   {i}. {project.get('id')} - {project.get('name')} (User: {project.get('user', 'None')})")
            return projects
        else:
            print(f"❌ Project List Failed: {response.text}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"❌ Project List Error: {e}")
        return []

def test_cache_clearing():
    """Test clearing the cache to see if it affects project listing."""
    try:
        print(f"\n🔄 Testing cache clearing")
        # Note: This endpoint might not exist, but worth trying
        response = requests.post(f"{API_BASE}/cache/clear", timeout=5)
        print(f"📊 Cache Clear Response: {response.status_code}")
        return True
    except requests.exceptions.RequestException:
        print("ℹ️  Cache clear endpoint not available (this is normal)")
        return True

def main():
    """Run all diagnostic tests."""
    print("🔍 DocReview360 Project Creation Diagnostic")
    print("=" * 50)

    # Test 1: API Health
    if not test_api_health():
        print("\n❌ API is not running. Please start the server first:")
        print("   python -m uvicorn src.docreview360.api:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)

    # Test 2: List initial projects
    initial_projects = test_project_list()

    # Test 3: Create new project
    new_project_id = test_project_creation()

    if new_project_id:
        # Test 4: Retrieve the new project
        test_project_retrieval(new_project_id)

        # Test 5: Clear cache
        test_cache_clearing()

        # Test 6: List projects again
        final_projects = test_project_list()

        # Test 7: Check if new project appears in list
        project_ids = [p.get('id') for p in final_projects]
        if new_project_id in project_ids:
            print(f"\n✅ SUCCESS: New project '{new_project_id}' appears in project list!")
        else:
            print(f"\n❌ ISSUE: New project '{new_project_id}' is NOT in project list!")
            print(f"   Available projects: {project_ids}")

            # Check if it's a caching issue
            print("\n🔄 Waiting 35 seconds for cache to expire...")
            import time
            time.sleep(35)

            print("🔄 Testing project list again after cache expiration...")
            final_projects_after_cache = test_project_list()
            project_ids_after_cache = [p.get('id') for p in final_projects_after_cache]

            if new_project_id in project_ids_after_cache:
                print(f"✅ CACHE ISSUE: Project appears after cache expiration!")
            else:
                print(f"❌ PERSISTENT ISSUE: Project still not appearing after cache expiration!")
    else:
        print("\n❌ Cannot proceed with tests - project creation failed")

    print("\n" + "=" * 50)
    print("🔍 Diagnostic Complete")

if __name__ == "__main__":
    main()
