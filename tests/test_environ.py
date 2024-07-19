import os

import pytest
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.environ import Environment
from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEnvironment

msg = {"_project": "mybot", "_spider": "myspider", "_job": "ID"}


@pytest.fixture()
def environ(tmpdir):
    config = Config(values={"eggs_dir": tmpdir, "logs_dir": tmpdir})
    config.cp.add_section("settings")
    config.cp.set("settings", "newbot", "newbot.settings")
    return Environment(config, initenv={})


def test_interface(environ):
    verifyObject(IEnvironment, environ)


def test_get_environment_with_eggfile(environ):
    env = environ.get_environment(msg, 3)

    assert env["SCRAPY_PROJECT"] == "mybot"
    assert "SCRAPY_SETTINGS_MODULE" not in env


@pytest.mark.parametrize("values", [{"items_dir": "../items"}, {"logs_dir": "../logs"}])
@pytest.mark.parametrize(("key", "value"), [("_project", "../p"), ("_spider", "../s"), ("_job", "../j")])
def test_get_environment_secure(values, key, value):
    config = Config(values=values)
    environ = Environment(config, initenv={})

    with pytest.raises(DirectoryTraversalError) as exc:
        environ.get_settings({**msg, key: value})

    assert str(exc.value) == (
        f"{value if key == '_project' else 'mybot'}{os.sep}"
        f"{value if key == '_spider' else 'myspider'}{os.sep}"
        f"{value if key == '_job' else 'ID'}.log"
    )
