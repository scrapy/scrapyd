import io
import os.path
import sys
from unittest.mock import patch

import pytest
from zope.interface import implementer

from scrapyd.exceptions import BadEggError
from scrapyd.interfaces import IEggStorage
from scrapyd.runner import main

BASEDIR = os.path.abspath(os.path.dirname(__file__))


@implementer(IEggStorage)
class MockEggStorage:
    def __init__(self, config):
        self.config = config

    def put(self, eggfile, project, version):
        pass

    def get(self, project, version=None):
        if project == "bytesio":
            with open(os.path.join(BASEDIR, "fixtures", "quotesbot.egg"), "rb") as f:
                return version, io.BytesIO(f.read())
        if project == "noentrypoint":
            with open(os.path.join(BASEDIR, "fixtures", "quotesbot_noentrypoint.egg"), "rb") as f:
                return version, io.BytesIO(f.read())
        if project == "badegg":
            return version, io.BytesIO(b"badegg")
        return None, None

    def list(self, project):
        pass

    def list_projects(self):
        return []

    def delete(self, project, version=None):
        pass


@pytest.mark.parametrize(
    "module",
    [
        "scrapy.utils.project",
        "scrapy.utils.conf",
        "scrapyd.interfaces",
        "scrapyd.runner",
    ],
)
def test_no_load_scrapy_conf(module):
    __import__(module)

    assert "scrapy.conf" not in sys.modules, f"module {module!r} must not cause the scrapy.conf module to be loaded"


@pytest.mark.skipif(sys.platform == "win32", reason="The temporary file encounters a PermissionError")
def test_bytesio(monkeypatch, capsys, chdir):
    (chdir / "scrapyd.conf").write_text("[scrapyd]\neggstorage = tests.test_runner.MockEggStorage")
    monkeypatch.setenv("SCRAPY_PROJECT", "bytesio")

    with patch.object(sys, "argv", ["scrapy", "list"]), pytest.raises(SystemExit) as exc:
        main()

    # main() sets SCRAPY_SETTINGS_MODULE, which interferes with other tests.
    del os.environ["SCRAPY_SETTINGS_MODULE"]

    captured = capsys.readouterr()

    assert exc.value.code == 0
    assert captured.out == "toscrape-css\ntoscrape-xpath\n"
    assert captured.err == ""


def test_badegg(monkeypatch, capsys, chdir):
    (chdir / "scrapyd.conf").write_text("[scrapyd]\neggstorage = tests.test_runner.MockEggStorage")
    monkeypatch.setenv("SCRAPY_PROJECT", "badegg")

    with patch.object(sys, "argv", ["scrapy", "list"]), pytest.raises(BadEggError) as exc:
        main()

    # main() sets SCRAPY_SETTINGS_MODULE, which interferes with other tests.
    os.environ.pop("SCRAPY_SETTINGS_MODULE", None)

    captured = capsys.readouterr()

    assert str(exc.value) == ""
    assert captured.out == ""
    assert captured.err == ""


# This confirms that entry_points are required, as documented.
@pytest.mark.filterwarnings("ignore:Module quotesbot was already imported from:UserWarning")  # fixture reuses module
def test_noentrypoint(monkeypatch, capsys, chdir):
    (chdir / "scrapyd.conf").write_text("[scrapyd]\neggstorage = tests.test_runner.MockEggStorage")
    monkeypatch.setenv("SCRAPY_PROJECT", "noentrypoint")

    with patch.object(sys, "argv", ["scrapy", "list"]), pytest.raises(AttributeError) as exc:
        main()

    # main() sets SCRAPY_SETTINGS_MODULE, which interferes with other tests.
    os.environ.pop("SCRAPY_SETTINGS_MODULE", None)

    captured = capsys.readouterr()

    assert str(exc.value)
    assert captured.out == ""
    assert captured.err == ""
