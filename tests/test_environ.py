import json
import os
import re
from unittest.mock import patch

import pytest
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.environ import Environment
from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEnvironment
from tests import has_settings


def test_interface(environ):
    verifyObject(IEnvironment, environ)


def test_get_settings(environ):
    settings = environ.get_settings({"_project": "p1", "_spider": "s1", "_job": "j1"})

    assert re.search(r"^\S+j1\.log$", settings["LOG_FILE"])

    if environ.items_dir:
        feeds = json.loads(settings.pop("FEEDS"))
        path, value = feeds.popitem()

        assert list(settings) == ["LOG_FILE"]
        assert feeds == {}
        assert re.search(r"^file:///\S+j1\.jl$", path)
        assert value == {"format": "jsonlines"}


@pytest.mark.parametrize(
    ("items_dir", "pattern"),
    [
        (
            "https://host.example/path?query=value#fragment",
            r"https://host\.example/path/p1/s1/j1\.jl\?query=value#fragment",
        ),
        (
            "https://host.example/path/",
            "https://host.example/path/p1/s1/j1.jl",  # no double slashes
        ),
        (
            "file:/root.dir/path?ignored#ignored",
            r"file:///([A-Z]:/)?root\.dir/path/p1/s1/j1\.jl",
        ),
        (
            "file://hostname/root.dir/path?ignored#ignored",
            r"file:///([A-Z]:/)?root.dir/path/p1/s1/j1.jl",
        ),
        (
            "file:///root.dir/path?ignored#ignored",
            r"file:///([A-Z]:/)?root.dir/path/p1/s1/j1.jl",
        ),
    ],
)
@patch("os.listdir", lambda _: [])
@patch("os.makedirs", lambda _: _)
def test_get_settings_url(items_dir, pattern):
    config = Config(values={"logs_dir": "", "items_dir": items_dir})
    environ = Environment(config, initenv={})

    settings = environ.get_settings({"_project": "p1", "_spider": "s1", "_job": "j1"})
    feeds = json.loads(settings.pop("FEEDS"))
    path, value = feeds.popitem()

    assert settings == {}
    assert feeds == {}
    assert re.search(pattern, path)
    assert value == {"format": "jsonlines"}


@pytest.mark.parametrize("values", [{"items_dir": "../items"}, {"logs_dir": "../logs"}])
@pytest.mark.parametrize(("key", "value"), [("_project", "../p"), ("_spider", "../s"), ("_job", "../j")])
def test_get_settings_secure(values, key, value):
    config = Config(values=values)
    environ = Environment(config, initenv={})

    with pytest.raises(DirectoryTraversalError) as exc:
        environ.get_settings({"_project": "p1", "_spider": "s1", "_job": "j1", key: value})

    assert str(exc.value) == (
        f"{value if key == '_project' else 'p1'}{os.sep}"
        f"{value if key == '_spider' else 's1'}{os.sep}"
        f"{value if key == '_job' else 'j1'}.log"
    )


def test_jobs_to_keep(chdir):
    config = Config(values={"jobs_to_keep": "2"})
    environ = Environment(config, initenv={})
    directory = chdir / "logs" / "p1" / "s1"

    assert not directory.exists()

    environ.get_settings({"_project": "p1", "_spider": "s1", "_job": "j1"})

    assert directory.exists()

    (directory / "j1.a").touch()
    (directory / "j2.b").touch()
    os.utime(directory / "j1.a", (1000000000, 1000000000))
    os.utime(directory / "j2.b", (1000000000, 1000000000))
    (directory / "j3.c").touch()
    (directory / "j4.d").touch()

    environ.get_settings({"_project": "p1", "_spider": "s1", "_job": "j1"})

    assert not (directory / "j1.a").exists()
    assert not (directory / "j2.b").exists()


@pytest.mark.parametrize(
    ("message", "run_only_if_has_settings"),
    [
        ({"_project": "mybot"}, False),
        ({"_project": "mybot", "_version": "v1"}, False),
        ({"_project": "localproject"}, True),
    ],
)
def test_get_environment(monkeypatch, environ, message, run_only_if_has_settings):
    if run_only_if_has_settings and not has_settings():
        pytest.skip("[settings] section is not set")

    monkeypatch.setenv("CUSTOM", "value")
    env = environ.get_environment(message, 3)

    assert env["CUSTOM"] == "value"
    assert env["SCRAPY_PROJECT"] == message["_project"]

    if "_version" in message:
        assert env["SCRAPYD_EGG_VERSION"] == "v1"
    else:
        assert "SCRAPYD_EGG_VERSION" not in env

    if run_only_if_has_settings:
        assert env["SCRAPY_SETTINGS_MODULE"] == "localproject.settings"
    else:
        assert "SCRAPY_SETTINGS_MODULE" not in env
