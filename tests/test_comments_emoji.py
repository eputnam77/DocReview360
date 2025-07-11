from docreview360.comments import add_comment, list_comments


def test_mentions_and_emoji() -> None:
    add_comment("d1", "alice", "Hi @bob :smile:")
    comments = list_comments("d1")
    assert comments[0].mentions == ["bob"]
    assert "😄" in comments[0].text
