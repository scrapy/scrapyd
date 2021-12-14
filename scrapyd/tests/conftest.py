import shutil
from pathlib import Path

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel
from zope.interface import implementer

from scrapyd import Config
from scrapyd.app import application
from scrapyd.interfaces import IEggStorage, ISpiderScheduler
from scrapyd.website import Root


@implementer(ISpiderScheduler)
class FakeScheduler:

    def __init__(self, config):
        self.config = config
        self.calls = []

    def schedule(self, project, spider_name, priority=0.0, **spider_args):
        self.calls.append(
            [project, spider_name]
        )

    def list_projects(self):
        return ['quotesbot']

    def update_projects(self):
        pass


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


def common_app_fixture(request):
    config = Config()

    app = application(config)
    project, version = 'quotesbot', '0.1'
    storage = app.getComponent(IEggStorage)
    app.setComponent(ISpiderScheduler, FakeScheduler(config))

    def delete_egg():
        # There is no egg initially but something can place an egg
        # e.g. addversion test
        delete_eggs(storage, project, version, config)

    request.addfinalizer(delete_egg)
    return Root(config, app), storage


@pytest.fixture
def site_no_egg(request):
    root, storage = common_app_fixture(request)
    return root


@pytest.fixture
def site_with_egg(request):
    root, storage = common_app_fixture(request)

    egg_path = Path(__file__).absolute().parent / "quotesbot.egg"
    project, version = 'quotesbot', '0.1'
    with open(egg_path, 'rb') as f:
        storage.put(f, project, version)

    return root
