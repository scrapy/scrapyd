import os.path
import shutil

import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.webservice import spider_list
from scrapyd.website import Root
from tests import root_add_version

BASEDIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture(autouse=True)
def _clear_spider_list_cache():
    spider_list.cache.clear()


@pytest.fixture()
def txrequest():
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(DummyChannel.TCP())
    return Request(http_channel)


# Use this fixture when testing the Scrapyd web UI or API or writing configuration files.
@pytest.fixture()
def chdir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(
    params=[
        None,
        (Config.SECTION, "items_dir", "items"),
        "scrapy.cfg",
    ],
    ids=["default", "items_dir", "settings"],
)
def app(request, chdir):
    if request.param == "scrapy.cfg":
        shutil.copytree(os.path.join(BASEDIR, "fixtures", "filesystem"), chdir, dirs_exist_ok=True)

    config = Config()
    if isinstance(request.param, tuple):
        config.cp.set(*request.param)

    return application(config)


@pytest.fixture(
    params=[
        None,
        (Config.SECTION, "items_dir", "items"),
        "scrapy.cfg",
    ],
    ids=["default", "items_dir", "settings"],
)
def root(request, chdir):
    if request.param == "scrapy.cfg":
        shutil.copytree(os.path.join(BASEDIR, "fixtures", "filesystem"), chdir, dirs_exist_ok=True)

    config = Config()
    if isinstance(request.param, tuple):
        config.cp.set(*request.param)

    return Root(config, application(config))


@pytest.fixture()
def root_with_egg(root):
    root_add_version(root, "quotesbot", "0.1", "quotesbot")
    root.update_projects()
    return root
