import tempfile

import pytest

from docreview360.records_keeper import create_archival_folder


def test_create_archival_folder_rejects_whitespace_id():
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            create_archival_folder(tmp, '   ')
