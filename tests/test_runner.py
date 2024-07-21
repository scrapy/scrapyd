import sys

import pytest


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
