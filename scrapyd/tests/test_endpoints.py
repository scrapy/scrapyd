import re

import pytest
import requests

from scrapyd.tests.mockserver import MockScrapyDServer


@pytest.fixture
def mock_scrapyd():
    with MockScrapyDServer() as server:
        yield server


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