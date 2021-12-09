import os

from twisted.trial import unittest

from zope.interface.verify import verifyObject

from scrapyd.interfaces import IEnvironment
from scrapyd.config import Config
from scrapyd.environ import Environment

class EnvironmentTest(unittest.TestCase):

    def setUp(self):
        d = self.mktemp()
        os.mkdir(d)
        config = Config(values={'eggs_dir': d, 'logs_dir': d})
        config.cp.add_section('settings')
        config.cp.set('settings', 'newbot', 'newbot.settings')
        self.environ = Environment(config, initenv={})

    def test_interface(self):
        verifyObject(IEnvironment, self.environ)

    def test_get_environment_with_eggfile(self):
        msg = {'_project': 'mybot', '_spider': 'myspider', '_job': 'ID'}
        slot = 3
        env = self.environ.get_environment(msg, slot)
        self.assertEqual(env['SCRAPY_PROJECT'], 'mybot')
        self.assertEqual(env['SCRAPY_SLOT'], '3')
        self.assertEqual(env['SCRAPY_SPIDER'], 'myspider')
        self.assertEqual(env['SCRAPY_JOB'], 'ID')
        self.assert_(env['SCRAPY_LOG_FILE'].endswith(os.path.join('mybot', 'myspider', 'ID.log')))
        if env.get('SCRAPY_FEED_URI'):  # Not compulsory
            self.assert_(env['SCRAPY_FEED_URI'].startswith('file://{}'.format(os.getcwd())))
            self.assert_(env['SCRAPY_FEED_URI'].endswith(os.path.join('mybot', 'myspider', 'ID.jl')))
        self.assertNotIn('SCRAPY_SETTINGS_MODULE', env)

    def test_get_environment_with_no_items_dir(self):
        config = Config(values={'items_dir': '', 'logs_dir': ''})
        config.cp.add_section('settings')
        config.cp.set('settings', 'newbot', 'newbot.settings')
        msg = {'_project': 'mybot', '_spider': 'myspider', '_job': 'ID'}
        slot = 3
        environ = Environment(config, initenv={})
        env = environ.get_environment(msg, slot)
        self.assertNotIn('SCRAPY_FEED_URI', env)
        self.assertNotIn('SCRAPY_LOG_FILE', env)
