import pytest

from scrapyd.launcher import get_crawl_args


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ({"_project": "p1", "_spider": "s1"}, ["s1"]),
        ({"_project": "p1", "_spider": "s1", "settings": {"ONE": "two"}}, ["s1", "-s", "ONE=two"]),
        ({"_project": "p1", "_spider": "s1", "arg1": "val1"}, ["s1", "-a", "arg1=val1"]),
        (
            {"_project": "p1", "_spider": "s1", "arg1": "val1", "settings": {"ONE": "two"}},
            ["s1", "-s", "ONE=two", "-a", "arg1=val1"],
        ),
    ],
)
def test_get_crawl_args(message, expected):
    assert get_crawl_args(message) == expected
