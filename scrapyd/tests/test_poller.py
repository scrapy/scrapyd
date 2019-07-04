import os
import time

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
        cfg = [('mybot2', 'spider2', 0),   # second
               ('mybot1', 'spider2', 0.0), # third
               ('mybot1', 'spider1', -1),  # fourth
               ('mybot1', 'spider3', 1.0)] # first
        for prj, spd, priority in cfg:
            self.queues[prj].add(spd, priority)
            if prj == 'mybot2':
                time.sleep(1.5)  # ensure different timestamp

        d1 = self.poller.next()
        d2 = self.poller.next()
        d3 = self.poller.next()
        d4 = self.poller.next()
        d5 = self.poller.next()
        self.failUnless(isinstance(d1, Deferred))
        self.failIf(hasattr(d1, 'result'))

        # first poll
        self.poller.poll()
        self.failUnless(hasattr(d1, 'result') and getattr(d1, 'called', False))
        self.assertEqual(d1.result, {'_project': 'mybot1', '_spider': 'spider3'})

        # second poll
        self.poller.poll()
        self.assertEqual(d2.result, {'_project': 'mybot2', '_spider': 'spider2'})

        # third poll
        self.poller.poll()
        self.assertEqual(d3.result, {'_project': 'mybot1', '_spider': 'spider2'})

        # fourth poll
        self.poller.poll()
        self.assertEqual(d4.result, {'_project': 'mybot1', '_spider': 'spider1'})

        # final poll
        self.poller.poll()
        self.failIf(hasattr(d5, 'result'))
