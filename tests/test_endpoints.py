import io
import os
import re

import pytest
import requests
from requests.models import Response

from scrapyd import __version__
from tests import get_egg_data
from tests.mockserver import MockScrapydServer


@pytest.fixture()
def mock_scrapyd(chdir):
    with MockScrapydServer() as server:
        yield server


@pytest.fixture()
def quotesbot_egg():
    return io.BytesIO(get_egg_data("quotesbot"))


@pytest.fixture()
def quotesbot_egg_asyncio():
    # This egg file contains settings with TWISTED_REACTOR set to asyncio ractor
    return io.BytesIO(get_egg_data("quotesbot_asyncio"))


def _deploy(mock_scrapyd, quotesbot_egg) -> Response:
    url = mock_scrapyd.urljoin("addversion.json")
    data = {b"project": b"quotesbot", b"version": b"0.01"}
    files = {b"egg": quotesbot_egg}
    return requests.post(url, data=data, files=files)


def test_urljoin(mock_scrapyd):
    assert mock_scrapyd.urljoin("foo") == f"{mock_scrapyd.url}foo"


def test_root(mock_scrapyd):
    response = requests.get(mock_scrapyd.url)

    assert response.status_code == 200
    assert re.search("To schedule a spider you need to use the API", response.text)


def test_auth():
    with MockScrapydServer(username="bob", password="hunter2") as server:
        assert requests.get(server.url).status_code == 401

        res = requests.get(server.url, auth=("bob", "hunter2"))

        assert res.status_code == 200
        assert re.search("To schedule a spider", res.text)

        res = requests.get(server.url, auth=("bob", "invalid"))

        assert res.status_code == 401

    stdout = server.stdout.decode()

    # scrapyd.basicauth
    assert f" [-] Basic authentication enabled{os.linesep}" in stdout
    # scrapyd.app
    assert f" [-] Scrapyd web console available at http://127.0.0.1:{server.http_port}/" in stdout
    # scrapyd.launcher
    assert re.search(
        f" \\[Launcher\\] Scrapyd {__version__} started: max_proc=\\d+, runner='scrapyd.runner'{os.linesep}", stdout
    )


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
    assert f" [_GenericHTTPChannelProtocol,0,127.0.0.1] Unhandled Error{os.linesep}" in stdout
    assert f"\tTraceback (most recent call last):{os.linesep}" in stdout
    assert "\ttwisted.web.error.Error: 200 project is invalid: " in stdout


@pytest.mark.parametrize(
    ("webservice", "method"),
    [
        ("daemonstatus", "GET"),
        ("addversion", "POST"),
        ("schedule", "POST"),
        ("cancel", "POST"),
        ("status", "GET"),
        ("listprojects", "GET"),
        ("listversions", "GET"),
        ("listspiders", "GET"),
        ("listjobs", "GET"),
        ("delversion", "POST"),
        ("delproject", "POST"),
    ],
)
def test_options(mock_scrapyd, webservice, method):
    response = requests.options(mock_scrapyd.urljoin(f"{webservice}.json"))

    assert response.status_code == 204, f"204 != {response.status_code}"
    assert response.content == b""
    assert response.headers["Allow"] == f"OPTIONS, HEAD, {method}"


def test_launch_spider_get(mock_scrapyd):
    response = requests.get(mock_scrapyd.urljoin("schedule.json"))

    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_spider_list_no_project(mock_scrapyd):
    response = requests.get(mock_scrapyd.urljoin("listspiders.json"))
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "error"
    assert data["message"] == "'project' parameter is required"


def test_spider_list_project_no_egg(mock_scrapyd):
    response = requests.get(mock_scrapyd.urljoin("listprojects.json"))
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "ok"


def test_addversion_and_delversion(mock_scrapyd, quotesbot_egg):
    response = _deploy(mock_scrapyd, quotesbot_egg)
    data = response.json()

    assert response.status_code == 200
    assert data["spiders"] == 2
    assert data["status"] == "ok"
    assert data["project"] == "quotesbot"

    url = mock_scrapyd.urljoin("delversion.json")
    res = requests.post(url, data={"project": "quotesbot", "version": "0.01"})

    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_failed_settings(mock_scrapyd, quotesbot_egg_asyncio):
    response = _deploy(mock_scrapyd, quotesbot_egg_asyncio)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
