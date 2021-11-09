import re

import aiohttp
import pytest
from aiohttp.web_response import Response

from scrapyd.tests.mockserver import MockScrapyDServer


@pytest.fixture
def mock_scrapyd():
    with MockScrapyDServer() as server:
        yield server


async def get_url(url) -> (str, Response):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            res_text = await resp.text()
            return res_text, resp


class TestEndpoint:
    def test_urljoin(self, mock_scrapyd):
        assert mock_scrapyd.urljoin("foo") == mock_scrapyd.url + 'foo'

    @pytest.mark.asyncio
    async def test_root(self, mock_scrapyd):
        root_text, resp = await get_url(mock_scrapyd.url)
        assert resp.status == 200
        assert re.search(
            "To schedule a spider you need to use the API",
            root_text
        )

