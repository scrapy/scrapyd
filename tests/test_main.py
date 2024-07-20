import pkgutil
import sys

import pytest

from scrapyd.__main__ import main

__version__ = pkgutil.get_data(__package__, "../scrapyd/VERSION").decode("ascii").strip()


def test_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrapyd", "junk", "--version", "junk"])
    main()

    assert capsys.readouterr().out == f"Scrapyd {__version__}\n"


def test_v(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrapyd", "junk", "-v", "junk"])
    main()

    assert capsys.readouterr().out == f"Scrapyd {__version__}\n"


def test_help(capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["scrapyd", "--help"])

    with pytest.raises(SystemExit):
        main()

    out = capsys.readouterr().out

    assert out.startswith("Usage: scrapyd [options]\n")
    assert "--nodaemon" not in out
    assert "python" not in out
    assert "rundir" not in out
    assert "ftp" not in out
    assert "Commands:" not in out
