from pathlib import Path

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.interfaces import IEggStorage
from scrapyd.website import Root


@pytest.fixture
def txrequest():
    tcp_channel = DummyChannel.TCP()
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(tcp_channel)
    return Request(http_channel)


@pytest.fixture
def site_no_egg():
    config = Config()
    app = application(config)
    return Root(config, app)


@pytest.fixture
def site_with_egg():
    config = Config()
    app = application(config)
    storage = app.getComponent(IEggStorage)
    egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
    with open(egg_path, 'rb') as f:
        storage.put(f, 'quotesbot', '0.1')
    return Root(config, app)

