import docreview360.comments as comments


def test_add_comment_parses_emojis_and_mentions_with_hyphen() -> None:
    comments.reset_comment_state()
    c = comments.add_comment("doc", "alice", "Hi @bob-smith :rocket:")
    assert c.mentions == ["bob-smith"]
    assert "🚀" in c.text
    # ``list_comments`` should include the newly created comment
    assert comments.list_comments("doc") == [c]


def test_add_comment_deduplicates_mentions() -> None:
    comments.reset_comment_state()
    c = comments.add_comment("doc", "alice", "Hello @bob @bob @bob")
    assert c.mentions == ["bob"]


def test_mentions_ignore_emails() -> None:
    comments.reset_comment_state()
    c = comments.add_comment("doc", "alice", "Contact bob@example.com or @alice")
    assert c.mentions == ["alice"]
