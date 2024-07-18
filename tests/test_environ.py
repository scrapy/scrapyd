import os

import pytest
from twisted.trial import unittest
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.environ import Environment
from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEnvironment

msg = {"_project": "mybot", "_spider": "myspider", "_job": "ID"}
slot = 3


class EnvironmentTest(unittest.TestCase):
    def setUp(self):
        d = self.mktemp()
        os.mkdir(d)
        config = Config(values={"eggs_dir": d, "logs_dir": d})
        config.cp.add_section("settings")
        config.cp.set("settings", "newbot", "newbot.settings")

        self.environ = Environment(config, initenv={})

    def test_interface(self):
        verifyObject(IEnvironment, self.environ)

    def test_get_environment_with_eggfile(self):
        env = self.environ.get_environment(msg, slot)

        self.assertEqual(env["SCRAPY_PROJECT"], "mybot")
        self.assertEqual(env["SCRAPYD_SLOT"], "3")
        self.assertEqual(env["SCRAPYD_SPIDER"], "myspider")
        self.assertEqual(env["SCRAPYD_JOB"], "ID")
        self.assertTrue(env["SCRAPYD_LOG_FILE"].endswith(os.path.join("mybot", "myspider", "ID.log")))
        if env.get("SCRAPYD_FEED_URI"):  # Not compulsory
            self.assertTrue(env["SCRAPYD_FEED_URI"].startswith(f"file://{os.getcwd()}"))
            self.assertTrue(env["SCRAPYD_FEED_URI"].endswith(os.path.join("mybot", "myspider", "ID.jl")))
        self.assertNotIn("SCRAPY_SETTINGS_MODULE", env)

    def test_get_environment_with_no_items_dir(self):
        config = Config(values={"items_dir": "", "logs_dir": ""})
        config.cp.add_section("settings")
        config.cp.set("settings", "newbot", "newbot.settings")

        environ = Environment(config, initenv={})
        env = environ.get_environment(msg, slot)

        self.assertNotIn("SCRAPYD_FEED_URI", env)
        self.assertNotIn("SCRAPYD_LOG_FILE", env)

    def test_get_environment_secure(self):
        for values in ({"items_dir": "../items"}, {"logs_dir": "../logs"}):
            with self.subTest(values=values):
                config = Config(values=values)

                environ = Environment(config, initenv={})
                for k, v in (("_project", "../p"), ("_spider", "../s"), ("_job", "../j")):
                    with self.subTest(key=k, value=v):
                        with pytest.raises(DirectoryTraversalError) as exc:
                            environ.get_environment({**msg, k: v}, slot)

                        self.assertEqual(
                            str(exc.value),
                            f"{v if k == '_project' else 'mybot'}{os.sep}"
                            f"{v if k == '_spider' else 'myspider'}{os.sep}"
                            f"{v if k == '_job' else 'ID'}.log",
                        )
