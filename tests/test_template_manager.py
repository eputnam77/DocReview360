from docreview360 import template_manager as tm


def test_upload_template_copies_metadata(tmp_path):
    tm.reset_template_store(root=tmp_path / "template_store.json")
    meta = {"a": 1}
    ver = tm.upload_template("name", b"data", meta)
    meta["a"] = 2
    assert ver.metadata["a"] == 1


def test_save_and_list_templates(tmp_path):
    tm.save_template("t1", "content", root=tmp_path)
    assert tm.list_templates(root=tmp_path) == ["t1"]
