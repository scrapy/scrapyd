import pkgutil
import sys

import pytest

from scrapyd.__main__ import main

__version__ = pkgutil.get_data(__package__, '../scrapyd/VERSION').decode('ascii').strip()


def test_print_version(capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['scrapyd', 'junk', '--version', 'junk'])
    main()

    assert capsys.readouterr().out == f"Scrapyd {__version__}\n"


def test_print_v(capsys, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['scrapyd', 'junk', '-v', 'junk'])
    main()

    assert capsys.readouterr().out == f"Scrapyd {__version__}\n"


def test_twisted_options(capsys, monkeypatch):
    """
    Test that the twisted options are correctly parsed.
    """
    monkeypatch.setattr(sys, 'argv', ['scrapyd', '--help'])

    with pytest.raises(SystemExit):
        main()

    assert 'twistd' in capsys.readouterr().out
