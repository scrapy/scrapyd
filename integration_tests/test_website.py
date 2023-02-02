from integration_tests import req


def test_root():
    req("get", "/")


def test_paths():
    for page in ("/jobs", "/logs"):
        req("get", page)
