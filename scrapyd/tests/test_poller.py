import os
import time

from twisted.trial import unittest
from twisted.internet.defer import Deferred

from zope.interface.verify import verifyObject

from scrapyd.interfaces import IPoller
from scrapyd.config import Config
from scrapyd.poller import QueuePoller
from scrapyd.contrib.fix_poll_order.poller import FixQueuePoller
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
        self.failUnless(isinstance(d1, Deferred))
        self.failIf(hasattr(d1, 'result'))

        # poll once
        self.poller.poll()
        self.failUnless(hasattr(d1, 'result') and getattr(d1, 'called', False))

        # which project got run: project1 or project2?
        self.failUnless(d1.result.get('_project'))
        prj = d1.result['_project']
        self.failUnlessEqual(d1.result['_spider'], cfg.pop(prj))

        self.queues[prj].pop()

        # poll twice
        # check that the other project's spider got to run
        self.poller.poll()
        prj, spd = cfg.popitem()
        self.failUnlessEqual(d2.result, {'_project': prj, '_spider': spd})


class FixQueuePollerTest(unittest.TestCase):

    def setUp(self):
        d = self.mktemp()
        eggs_dir = os.path.join(d, 'eggs')
        dbs_dir = os.path.join(d, 'dbs')
        os.makedirs(eggs_dir)
        os.makedirs(dbs_dir)
        os.makedirs(os.path.join(eggs_dir, 'mybot1'))
        os.makedirs(os.path.join(eggs_dir, 'mybot2'))
        config = Config(values={'eggs_dir': eggs_dir, 'dbs_dir': dbs_dir,
                                'fix_poll_order': 'on'})
        self.queues = get_spider_queues(config)
        self.poller = FixQueuePoller(config)

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
                time.sleep(2)  # ensure different timestamp

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
