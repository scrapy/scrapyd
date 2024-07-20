from configparser import NoOptionError, NoSectionError

import pytest

from scrapyd import get_application
from scrapyd.app import application
from scrapyd.config import Config
from scrapyd.exceptions import InvalidUsernameError


def test_items_no_section():
    with pytest.raises(NoSectionError):
        Config().items("nonexistent")


def test_get_no_section():
    with pytest.raises(NoOptionError):
        Config().get("nonexistent")


def test_get_no_option():
    config = Config()
    config.cp.set("scrapyd", "http_port", "8000")

    with pytest.raises(NoOptionError):
        config.get("nonexistent")


def test_closest_scrapy_cfg(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "scrapy.cfg").write_text("[scrapyd]\nhttp_port = 1234")

    assert Config().getint("http_port") == 1234


def test_invalid_username():
    config = Config()
    config.cp.set("scrapyd", "username", "invalid:")

    with pytest.raises(InvalidUsernameError) as exc:
        application(config)

    assert (
        str(exc.value)
        == "The `username` option contains illegal character ':'. Check and update the Scrapyd configuration file."
    )


def test_invalid_username_sys():
    config = Config()
    config.cp.set("scrapyd", "username", "invalid:")

    with pytest.raises(SystemExit) as exc:
        get_application(config)

    assert (
        str(exc.value)
        == "The `username` option contains illegal character ':'. Check and update the Scrapyd configuration file."
    )
