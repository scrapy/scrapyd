import shutil
from pathlib import Path

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.interfaces import IEggStorage
from scrapyd.website import Root


def delete_eggs(storage, project, version, config):
    if storage.list(project) != []:
        storage.delete(project, version)
        eggdir = config.get("eggs_dir")
        shutil.rmtree(eggdir)


@pytest.fixture
def txrequest():
    tcp_channel = DummyChannel.TCP()
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(tcp_channel)
    return Request(http_channel)


@pytest.fixture
def site_no_egg(request):
    config = Config()
    app = application(config)
    project, version = 'quotesbot', '0.1'
    storage = app.getComponent(IEggStorage)

    def delete_egg():
        # There is no egg initially but something can place an egg
        # e.g. addversion test
        delete_eggs(storage, project, version, config)

    request.addfinalizer(delete_egg)
    return Root(config, app)


@pytest.fixture
def site_with_egg(request):
    config = Config()
    app = application(config)
    storage = app.getComponent(IEggStorage)
    egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
    project, version = 'quotesbot', '0.1'
    with open(egg_path, 'rb') as f:
        storage.put(f, project, version)

    def delete_egg():
        delete_eggs(storage, project, version, config)

    request.addfinalizer(delete_egg)
    return Root(config, app)

