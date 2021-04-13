import os

from twisted.trial import unittest
from twisted.internet.defer import Deferred

from zope.interface.verify import verifyObject

from scrapyd.interfaces import IPoller
from scrapyd.config import Config
from scrapyd.poller import QueuePoller
from scrapyd.utils import get_spider_queues

class QueuePollerTest(unittest.TestCase):

    def setUp(self):
        d = self.mktemp()
        eggs_dir = os.path.join(d, 'eggs')
        dbs_dir = os.path.join(d, 'dbs')
        os.makedirs(eggs_dir)
        os.makedirs(dbs_dir)
        os.makedirs(os.path.join(eggs_dir, 'mybot1'))
        os.makedirs(os.path.join(eggs_dir, 'mybot2'))
        config = Config(values={'eggs_dir': eggs_dir, 'dbs_dir': dbs_dir})
        self.queues = get_spider_queues(config)
        self.poller = QueuePoller(config)

    def test_interface(self):
        verifyObject(IPoller, self.poller)

    def test_poll_next(self):
        cfg = {'mybot1': 'spider1',
               'mybot2': 'spider2'}
        priority = 0
        for prj, spd in cfg.items():
            self.queues[prj].add(spd, priority)

        d1 = self.poller.next()
        d2 = self.poller.next()
        self.assertIsInstance(d1, Deferred)
        self.assertFalse(hasattr(d1, 'result'))

        # poll once
        self.poller.poll()
        self.assertTrue(hasattr(d1, 'result'))
        self.assertTrue(getattr(d1, 'called', False))

        # which project got run: project1 or project2?
        self.assertTrue(d1.result.get('_project'))
        prj = d1.result['_project']
        self.assertEqual(d1.result['_spider'], cfg.pop(prj))

        self.queues[prj].pop()

        # poll twice
        # check that the other project's spider got to run
        self.poller.poll()
        prj, spd = cfg.popitem()
        self.assertEqual(d2.result, {'_project': prj, '_spider': spd})
