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

BASEDIR = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture()
def txrequest():
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(DummyChannel.TCP())
    return Request(http_channel)


# Use this fixture when testing the Scrapyd web UI or API or writing configuration files.
@pytest.fixture()
def chdir(monkeypatch, tmpdir):
    monkeypatch.chdir(tmpdir)
    return tmpdir


@pytest.fixture(
    params=[
        None,
        (Config.SECTION, "items_dir", "items"),
        ("settings", "localproject", "localproject.settings"),
    ],
    ids=["default", "items_dir", "settings"],
)
def root(request, chdir):
    config = Config()
    if request.param:
        if request.param[0] == "settings":
            config.cp.add_section(request.param[0])
            # Copy the local files to be in the Python path.
            shutil.copytree(os.path.join(BASEDIR, "fixtures", "filesystem"), os.path.join(chdir), dirs_exist_ok=True)
        config.cp.set(*request.param)

    return Root(config, application(config))


@pytest.fixture()
def root_with_egg(root):
    root_add_version(root, "quotesbot", "0.1", "quotesbot")
    root.update_projects()
    return root
