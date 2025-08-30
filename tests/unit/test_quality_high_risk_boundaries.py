import json
import os
import tempfile

from docreview360 import quality


def test_high_risk_warnings_match_whole_words():
    data = ["term"]
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    try:
        quality.initialize_high_risk_terms(path)
        assert quality.high_risk_warnings("deterministic outcome") == []
    finally:
        os.remove(path)
        quality.initialize_high_risk_terms()
