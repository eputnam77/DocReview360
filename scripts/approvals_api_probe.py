import requests

# First, let's create a new project and see the full response
project_data = {
    "name": "Test Project with Auto Approvals 2",
    "document_number": "TEST-002",
    "phase": "Public Comment / Proposed Rulemaking",
    "workflow": "Public Comment / Proposed Rulemaking",
}
response = requests.post("http://localhost:8000/projects", json=project_data)
project = response.json()
print(f'Project created: {project["id"]}')
print(f'Workflow ID: {project["workflow"]}')
print(f"Full project response: {project}")

# List all workflows
workflows = requests.get("http://localhost:8000/workflows").json()
print(f"\nAll workflows: {workflows}")

# Check approvals for the workflow
if project["workflow"]:
    workflow_id = project["workflow"]
    approvals = requests.get(f"http://localhost:8000/approvals?workflow={workflow_id}").json()
    print(f"\nFound {len(approvals)} approvals for workflow {workflow_id}:")
    for approval in approvals:
        print(f'- {approval["reviewer"]}: {approval["description"]}')

    # Also check the workflow details
    workflow = requests.get(f"http://localhost:8000/workflows/{workflow_id}").json()
    print(f"\nWorkflow data: {workflow}")
    print(f"Workflow keys: {list(workflow.keys())}")
