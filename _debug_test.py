
import sys, os, importlib
sys.path.insert(0, 'tests')

# Simulate pytest's conftest.py loading
os.environ.setdefault('DOCREVIEW360_SECRET_KEY', 'test-secret')
os.environ.setdefault('DOCREVIEW360_ALGORITHM', 'HS256')
os.environ.setdefault('DOCREVIEW360_ACCESS_EXPIRE_MINUTES', '30')
os.environ.setdefault('DOCREVIEW360_TOKEN_ISSUER', 'test-issuer')
os.environ.setdefault('DOCREVIEW360_TOKEN_AUDIENCE', 'test-audience')

import docreview360.workflows as wf_initial
import docreview360.api as api_mod

print('Initial state:')
print('  Phase Link Test Flow in defs:', 'Phase Link Test Flow' in wf_initial.workflow_template_definitions)
print('  Phase Link Test Flow in wf_templates:', 'Phase Link Test Flow' in wf_initial.workflow_templates)
print('  _TEMPLATES_LOADED:', wf_initial._TEMPLATES_LOADED)

# Simulate test_register_callback_url (with monkeypatch.setenv)
os.environ['DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP'] = '1'
workflows_mod = importlib.reload(importlib.import_module('docreview360.workflows'))
# After reload, monkeypatch undoes:
del os.environ['DOCREVIEW360_SKIP_SAMPLE_BOOTSTRAP']
workflows_mod.workflows.clear()

print()
print('After test_register_callback_url:')
print('  _TEMPLATES_LOADED:', workflows_mod._TEMPLATES_LOADED)
print('  Phase Link Test Flow in defs:', 'Phase Link Test Flow' in workflows_mod.workflow_template_definitions)
print('  Phase Link Test Flow in wf_templates:', 'Phase Link Test Flow' in workflows_mod.workflow_templates)
print('  api.workflow_templates is wf.workflow_templates:', api_mod.workflow_templates is workflows_mod.workflow_templates)

# After the test, autouse _set_env monkeypatch is applied for next test
# (doesn't change WORKFLOW_TEMPLATES_FILE)

# Simulate the phases test
from fastapi.testclient import TestClient
from docreview360.api import app
client = TestClient(app)

resp = client.post('/workflow-templates', json={'name': 'Phase Link Test Flow', 'description': 'test', 'steps': [{'role': 'Reviewer', 'required': True}]})
print()
print('POST status:', resp.status_code, resp.json() if resp.status_code != 201 else 'created')
print('After POST:')
print('  Phase Link Test Flow in defs:', 'Phase Link Test Flow' in workflows_mod.workflow_template_definitions)
print('  Phase Link Test Flow in wf_templates:', 'Phase Link Test Flow' in workflows_mod.workflow_templates)
print('  Phase Link Test Flow in api.workflow_templates:', 'Phase Link Test Flow' in api_mod.workflow_templates)

client.post('/phases', json={'name': 'Phase Link Test'})

resp4 = client.put('/phases/Phase%20Link%20Test/workflow-template', json={'workflow_template_id': 'Phase Link Test Flow'})
print()
print('PUT status:', resp4.status_code)
if resp4.status_code == 404:
    # Check what get_workflow_template returns
    from docreview360.workflows import get_workflow_template
    tmpl = get_workflow_template('Phase Link Test Flow')
    print('get_workflow_template result:', tmpl)
    print('After get_workflow_template call:')
    print('  Phase Link Test Flow in defs:', 'Phase Link Test Flow' in workflows_mod.workflow_template_definitions)
    print('  Phase Link Test Flow in wf_templates:', 'Phase Link Test Flow' in workflows_mod.workflow_templates)
