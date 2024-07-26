import sys

import pytest

from scrapyd import __version__
from scrapyd.__main__ import main


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

    with pytest.raises(SystemExit) as exc:
        main()

    captured = capsys.readouterr()

    assert exc.value.code == 0
    assert captured.out.startswith("Usage: scrapyd [options]\n")
    assert "--nodaemon" in captured.out
    assert "python" not in captured.out
    assert "rundir" not in captured.out
    assert "ftp" not in captured.out
    assert "Commands:" not in captured.out
    assert captured.err == ""
