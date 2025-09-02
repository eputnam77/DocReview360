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
