from docreview360.email_templates import (
    create_template,
    delete_template,
    get_template,
    list_templates,
    update_template,
)


def test_create_and_get_template() -> None:
    tpl = create_template("review", "Review {doc}", "Body {doc}")
    assert get_template("review") == tpl


def test_update_and_delete_template() -> None:
    create_template("follow", "sub", "body")
    update_template("follow", subject="Follow up", task="follow_task")
    tpl = get_template("follow")
    assert tpl.subject == "Follow up" and tpl.task == "follow_task"
    delete_template("follow")
    assert get_template("follow") is None


def test_list_templates_order() -> None:
    create_template("a", "s", "b")
    create_template("b", "s", "b")
    names = [t.name for t in list_templates()]
    assert names[-2:] == ["a", "b"]
