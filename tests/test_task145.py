import subprocess

import pytest
from docreview360.stubs.task145 import task145


def test_task145_completed(monkeypatch) -> None:
    called = {}

    def fake_call(args):
        called["cmd"] = args

    monkeypatch.setattr(subprocess, "check_call", fake_call)
    task145("df_plugin")
    assert called["cmd"][3] == "install"


def test_install_plugin_validation(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "check_call", lambda *a, **k: None)
    from docreview360.plugin_marketplace import install_plugin

    with pytest.raises(ValueError):
        install_plugin("")
