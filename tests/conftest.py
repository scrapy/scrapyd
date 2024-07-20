import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.website import Root
from tests import clean, root_add_version


@pytest.fixture()
def txrequest():
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(DummyChannel.TCP())
    return Request(http_channel)


@pytest.fixture(params=[None, ("scrapyd", "items_dir", "items")], ids=["default", "items_dir"])
def root(request):
    config = Config()
    if request.param:
        config.cp.set(*request.param)

    app = application(config)

    yield Root(config, app)

    for setting in ("dbs_dir", "eggs_dir"):
        clean(config, setting)


@pytest.fixture()
def root_with_egg(root):
    root_add_version(root, "quotesbot", "0.1", "quotesbot")
    root.update_projects()
    return root
