from integration_tests import req


def test_root():
    response = req("get", "/")

    assert '"/jobs"' in response.text
    assert '"/logs/"' in response.text


def test_paths():
    for page in ("/jobs", "/logs"):
        req("get", page)


def test_base_path():
    response = req("get", "/", headers={"X-Forwarded-Prefix": "/base/path"})

    assert '"/base/path/jobs"' in response.text
    assert '"/base/path/logs/"' in response.text
