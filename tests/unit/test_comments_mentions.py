import docreview360.comments as comments


def test_add_comment_parses_emojis_and_mentions_with_hyphen():
    comments._comments.clear()
    c = comments.add_comment('doc', 'alice', 'Hi @bob-smith :rocket:')
    assert c.mentions == ['bob-smith']
    assert '🚀' in c.text
    # ``list_comments`` should include the newly created comment
    assert comments.list_comments('doc') == [c]
