from configparser import NoOptionError, NoSectionError

import pytest

from scrapyd.config import Config


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
