import importlib
from pathlib import Path

import pytest


def test_save_and_list_template(tmp_path: Path):
    # Import within test to capture NameError before fix
    tm = importlib.import_module('docreview360.template_manager')
    # use temporary root
    path = tm.save_template('sample', 'hello', root=tmp_path)
    assert path.read_text() == 'hello'
    assert tm.list_templates(root=tmp_path) == ['sample']


def test_upload_template_rejects_non_dict_metadata(tmp_path: Path):
    tm = importlib.import_module('docreview360.template_manager')
    with pytest.raises(ValueError):
        tm.upload_template('bad', b'data', metadata=['oops'])


def test_upload_template_requires_name():
    tm = importlib.import_module('docreview360.template_manager')
    with pytest.raises(ValueError):
        tm.upload_template('', b'data')


def test_upload_template_copies_metadata(tmp_path: Path):
    tm = importlib.import_module('docreview360.template_manager')
    tm._template_store.clear()
    meta = {"a": {"b": 1}}
    rec = tm.upload_template('name', b'data', metadata=meta)
    meta["a"]["b"] = 2
    assert rec.metadata == {"a": {"b": 1}}


def test_template_version_management(tmp_path: Path):
    tm = importlib.import_module('docreview360.template_manager')
    tm._template_store.clear()
    r1 = tm.upload_template('n', b'1')
    r2 = tm.upload_template('n', b'2')
    assert r1.version == 1 and r2.version == 2
    assert tm.get_latest_template('n') is r2
    assert tm.list_template_versions('n') == [r1, r2]
    tm.approve_template('n')
    tm.retire_template('n')
    assert r2.approved and r2.retired
    assert tm.list_stored_templates() == {'n': r2}
    with pytest.raises(ValueError):
        tm.approve_template('missing')
    with pytest.raises(ValueError):
        tm.retire_template('missing')


def test_list_templates_empty(tmp_path: Path):
    tm = importlib.import_module('docreview360.template_manager')
    assert tm.list_templates(root=tmp_path / 'none') == []


def test_save_template_requires_name(tmp_path: Path):
    tm = importlib.import_module('docreview360.template_manager')
    with pytest.raises(ValueError):
        tm.save_template('', 'x', root=tmp_path)
