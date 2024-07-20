import io
import re

import pytest
import requests
from requests.models import Response

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
    assert mock_scrapyd.urljoin("foo") == mock_scrapyd.url + "foo"


def test_root(mock_scrapyd):
    resp = requests.get(mock_scrapyd.url)

    assert resp.status_code == 200
    assert re.search("To schedule a spider you need to use the API", resp.text)


def test_auth():
    username, password = "Leonardo", "hunter2"

    with MockScrapydServer(authentication=username + ":" + password) as server:
        assert requests.get(server.url).status_code == 401

        res = requests.get(server.url, auth=(username, password))

        assert res.status_code == 200
        assert re.search("To schedule a spider", res.text)

        res = requests.get(server.url, auth=(username, "trying to hack"))

        assert res.status_code == 401


def test_launch_spider_get(mock_scrapyd):
    resp = requests.get(mock_scrapyd.urljoin("schedule.json"))

    assert resp.status_code == 200
    assert resp.json()["status"] == "error"


def test_spider_list_no_project(mock_scrapyd):
    resp = requests.get(mock_scrapyd.urljoin("listspiders.json"))
    data = resp.json()

    assert resp.status_code == 200
    assert data["status"] == "error"
    assert data["message"] == "'project' parameter is required"


def test_spider_list_project_no_egg(mock_scrapyd):
    resp = requests.get(mock_scrapyd.urljoin("listprojects.json"))
    data = resp.json()

    assert resp.status_code == 200
    assert data["status"] == "ok"


def test_addversion_and_delversion(mock_scrapyd, quotesbot_egg):
    resp = _deploy(mock_scrapyd, quotesbot_egg)
    data = resp.json()

    assert resp.status_code == 200
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
