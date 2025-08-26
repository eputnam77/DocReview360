import datetime as dt

from docreview360 import comments


def test_comment_timestamp_unique_and_mentions_isolated(monkeypatch):
    class FakeDateTime:
        calls = 0

        @classmethod
        def now(cls, tz):
            cls.calls += 1
            return dt.datetime(2020, 1, 1, tzinfo=tz) + dt.timedelta(seconds=cls.calls)

    monkeypatch.setattr(comments, "datetime", FakeDateTime)
    comments._comments.clear()

    c1 = comments.add_comment("doc", "user", "hello")
    c2 = comments.add_comment("doc", "user", "hello again")

    assert c1.created < c2.created
    c1.mentions.append("someone")
    assert c2.mentions == []

