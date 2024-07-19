import sys

SETTINGS_SAFE_MODULES = (
    "scrapy.utils.project",
    "scrapy.utils.conf",
    "scrapyd.interfaces",
    "scrapyd.runner",
)


def test_modules_that_shouldnt_load_settings():
    sys.modules.pop("scrapy.conf", None)
    for m in SETTINGS_SAFE_MODULES:
        __import__(m)

        assert "scrapy.conf" not in sys.modules, f"Module {m!r} must not cause the scrapy.conf module to be loaded"
