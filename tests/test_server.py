import io
import os
import re

import pytest
import requests

from tests import get_egg_data
from tests.mockserver import MockScrapydServer


@pytest.fixture()
def mock_scrapyd(chdir):
    with MockScrapydServer() as server:
        yield server


def test_urljoin(mock_scrapyd):
    assert mock_scrapyd.urljoin("foo") == f"{mock_scrapyd.url}foo"


def test_auth():
    with MockScrapydServer(username="bob", password="hunter2") as server:
        assert requests.get(server.url).status_code == 401

        res = requests.get(server.url, auth=("bob", "hunter2"))

        assert res.status_code == 200
        assert re.search("use the API", res.text)

        res = requests.get(server.url, auth=("bob", "invalid"))

        assert res.status_code == 401

    stdout = server.stdout.decode()

    # scrapyd.basicauth
    assert f" [-] Basic authentication enabled{os.linesep}" in stdout
    # scrapyd.app
    assert f" [-] Scrapyd web console available at http://127.0.0.1:{server.http_port}/" in stdout


def test_noauth():
    with MockScrapydServer() as server:
        pass

    # scrapyd.basicauth
    assert (
        f" [-] Basic authentication disabled as either `username` or `password` is unset{os.linesep}"
        in server.stdout.decode()
    )


def test_error():
    with MockScrapydServer() as server:
        requests.get(server.urljoin("listversions.json"), params={"project": [b"\xc3\x28"]})

    stdout = server.stdout.decode()

    # scrapyd.webservice
    assert f" [-] Unhandled Error{os.linesep}" in stdout
    assert f"\tTraceback (most recent call last):{os.linesep}" in stdout
    assert "\ttwisted.web.error.Error: 200 project is invalid: " in stdout


@pytest.mark.parametrize(
    ("method", "basename"),
    [
        ("GET", "daemonstatus"),
        ("POST", "addversion"),
        ("POST", "schedule"),
        ("POST", "cancel"),
        ("GET", "status"),
        ("GET", "listprojects"),
        ("GET", "listversions"),
        ("GET", "listspiders"),
        ("GET", "listjobs"),
        ("POST", "delversion"),
        ("POST", "delproject"),
    ],
)
def test_options(mock_scrapyd, method, basename):
    response = requests.options(mock_scrapyd.urljoin(f"{basename}.json"))

    assert response.status_code == 204, f"204 != {response.status_code}"
    assert response.content == b""
    assert response.headers["Allow"] == f"OPTIONS, HEAD, {method}"


# https://github.com/scrapy/scrapyd/issues/377
def test_other_reactors(mock_scrapyd):
    response = requests.post(
        mock_scrapyd.urljoin("addversion.json"),
        data={b"project": b"quotesbot", b"version": b"0.01"},
        # The egg's quotesbot/settings.py file sets TWISTED_REACTOR to
        # "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
        files={b"egg": io.BytesIO(get_egg_data("quotesbot_asyncio"))},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
