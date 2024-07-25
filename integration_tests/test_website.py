import pytest

from integration_tests import req


def test_root():
    response = req("get", "/")

    assert '"/jobs"' in response.text
    assert '"/logs/"' in response.text


@pytest.mark.parametrize(("path", "content"), [("jobs", "Cancel"), ("logs", "Last modified")])
def test_paths(path, content):
    response = req("get", f"/{path}")

    assert content in response.text


def test_base_path():
    response = req("get", "/", headers={"X-Forwarded-Prefix": "/path/to"})

    assert '"/path/to/jobs"' in response.text
    assert '"/path/to/logs/"' in response.text
