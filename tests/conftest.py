import shutil

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel
from zope.interface import implementer

from scrapyd import Config
from scrapyd.app import application
from scrapyd.interfaces import IEggStorage, ISpiderScheduler
from scrapyd.website import Root
from tests import root_add_version


@implementer(ISpiderScheduler)
class FakeScheduler:
    def __init__(self, config):
        self.config = config
        self.calls = []
        self.queues = {}

    def schedule(self, project, spider_name, priority=0.0, **spider_args):
        self.calls.append([project, spider_name])

    def list_projects(self):
        return ["quotesbot"]

    def update_projects(self):
        pass


@pytest.fixture()
def txrequest():
    tcp_channel = DummyChannel.TCP()
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(tcp_channel)
    return Request(http_channel)


@pytest.fixture(params=[None, ("scrapyd", "items_dir", "items")], ids=["default", "default_with_local_items"])
def site_no_egg(request):
    config = Config()
    if request.param:
        config.cp.set(*request.param)

    app = application(config)
    app.setComponent(ISpiderScheduler, FakeScheduler(config))

    yield Root(config, app)

    # There is no egg initially but something can place an egg
    # e.g. addversion test
    eggstorage = app.getComponent(IEggStorage)
    if eggstorage.list("quotesbot") != []:
        eggstorage.delete("quotesbot", "0.1")
        eggdir = config.get("eggs_dir")
        shutil.rmtree(eggdir)


@pytest.fixture()
def site_with_egg(site_no_egg):
    root_add_version(site_no_egg, "quotesbot", "0.1", "quotesbot")
    return site_no_egg
