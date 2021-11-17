import re
from pathlib import Path

import pytest
import requests
from requests.models import Response

from scrapyd.tests.mockserver import MockScrapyDServer


@pytest.fixture
def mock_scrapyd():
    with MockScrapyDServer() as server:
        yield server


@pytest.fixture
def quotesbot_egg():
    eggpath = Path(__file__).absolute().parent / "quotesbot.egg"
    with open(eggpath, 'rb') as egg:
        yield egg


@pytest.fixture
def quotesbot_egg_asyncio():
    # This egg file contains settings with TWISTED_REACTOR set to asyncio ractor
    eggpath = Path(__file__).absolute().parent / "quotesbot_asyncio.egg"
    with open(eggpath, 'rb') as egg:
        yield egg


class TestEndpoint:
    def test_urljoin(self, mock_scrapyd):
        assert mock_scrapyd.urljoin("foo") == mock_scrapyd.url + 'foo'

    def test_root(self, mock_scrapyd):
        resp = requests.get(mock_scrapyd.url)
        assert resp.status_code == 200
        assert re.search(
            "To schedule a spider you need to use the API",
            resp.text
        )

    def test_auth(self):
        username, password = "Leonardo", "hunter2"
        with MockScrapyDServer(
                authentication=username + ":" + password
        ) as server:
            assert requests.get(server.url).status_code == 401
            res = requests.get(server.url, auth=(username, password))
            assert res.status_code == 200
            assert re.search("To schedule a spider", res.text)
            res = requests.get(server.url, auth=(username, "trying to hack"))
            assert res.status_code == 401

    def test_launch_spider_get(self, mock_scrapyd):
        resp = requests.get(mock_scrapyd.urljoin("schedule.json"))
        assert resp.status_code == 200
        # TODO scrapyd should return status 405 Method Not Allowed not 200
        assert resp.json()['status'] == 'error'

    def test_spider_list_no_project(self, mock_scrapyd):
        resp = requests.get(mock_scrapyd.urljoin("listspiders.json"))
        assert resp.status_code == 200
        # TODO scrapyd should return status 400 if no project specified
        data = resp.json()
        assert data['status'] == 'error'
        assert data['message'] == "'project'"

    def test_spider_list_project_no_egg(self, mock_scrapyd):
        resp = requests.get(mock_scrapyd.urljoin('listprojects.json'))
        data = resp.json()
        assert resp.status_code == 200
        assert data['projects'] == []

    def test_addversion_and_delversion(self, mock_scrapyd, quotesbot_egg):
        resp = self._deploy(mock_scrapyd, quotesbot_egg)
        assert resp.status_code == 200
        data = resp.json()
        assert data['spiders'] == 2
        assert data['status'] == 'ok'
        assert data['project'] == 'quotesbot'
        url = mock_scrapyd.urljoin('delversion.json')
        res = requests.post(url, data={'project': 'quotesbot',
                                       "version": "0.01"})
        assert res.status_code == 200
        assert res.json()['status'] == 'ok'

    def _deploy(self, mock_scrapyd, quotesbot_egg) -> Response:
        url = mock_scrapyd.urljoin("addversion.json")
        data = {
            b"project": b"quotesbot",
            b"version": b"0.01"
        }
        files = {
            b'egg': quotesbot_egg
        }
        resp = requests.post(url, data=data, files=files)
        return resp

    def test_addversion_and_schedule(self, mock_scrapyd, quotesbot_egg):
        deploy_response = self._deploy(mock_scrapyd, quotesbot_egg)
        assert deploy_response.status_code == 200
        schedule_url = mock_scrapyd.urljoin('schedule.json')
        data = {
            'spider': 'toscrape-css',
            'project': 'quotesbot',
            # Spider making request to scrapyD root url
            # TODO add some mock website later, for now we just want
            # to make sure spider is launched properly, not important
            # if it collects any items or not
            'start_url': mock_scrapyd.url
        }
        schedule_res = requests.post(schedule_url, data=data)
        assert schedule_res.status_code == 200
        data = schedule_res.json()
        assert 'jobid' in data
        assert data['status'] == 'ok'

    @pytest.mark.xfail(reason='asyncio reactor not supported yet')
    def test_failed_settings(self, mock_scrapyd, quotesbot_egg_asyncio):
        response = self._deploy(mock_scrapyd, quotesbot_egg_asyncio)
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'
