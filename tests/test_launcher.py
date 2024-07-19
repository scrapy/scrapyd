from scrapyd.launcher import get_crawl_args


def test_get_crawl_args():
    msg = {"_project": "lolo", "_spider": "lala"}

    assert get_crawl_args(msg) == ["lala"]

    msg = {"_project": "lolo", "_spider": "lala", "arg1": "val1"}
    cargs = get_crawl_args(msg)

    assert cargs == ["lala", "-a", "arg1=val1"]
    assert all(isinstance(x, str) for x in cargs), cargs


def test_get_crawl_args_with_settings():
    msg = {"_project": "lolo", "_spider": "lala", "arg1": "val1", "settings": {"ONE": "two"}}
    cargs = get_crawl_args(msg)

    assert cargs == ["lala", "-a", "arg1=val1", "-s", "ONE=two"]
    assert all(isinstance(x, str) for x in cargs), cargs
