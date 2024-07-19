import sys
import unittest


class SettingsSafeModulesTest(unittest.TestCase):
    # these modules must not load scrapy.conf
    SETTINGS_SAFE_MODULES = (
        "scrapy.utils.project",
        "scrapy.utils.conf",
        "scrapyd.interfaces",
        "scrapyd.runner",
    )

    def test_modules_that_shouldnt_load_settings(self):
        sys.modules.pop("scrapy.conf", None)
        for m in self.SETTINGS_SAFE_MODULES:
            __import__(m)

            self.assertNotIn(
                "scrapy.conf", sys.modules, f"Module {m!r} must not cause the scrapy.conf module to be loaded"
            )


if __name__ == "__main__":
    unittest.main()
