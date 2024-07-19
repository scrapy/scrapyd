import os.path
import shutil

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.website import Root
from tests import root_add_version


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

    yield Root(config, app)

    for setting in ("dbs_dir", "eggs_dir"):
        directory = os.path.realpath(config.get(setting))
        parent = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
        # Avoid accidentally deleting directories outside the project.
        assert os.path.commonprefix((directory, parent)) == parent
        shutil.rmtree(directory)


@pytest.fixture()
def site_with_egg(site_no_egg):
    root_add_version(site_no_egg, "quotesbot", "0.1", "quotesbot")
    site_no_egg.update_projects()
    return site_no_egg
