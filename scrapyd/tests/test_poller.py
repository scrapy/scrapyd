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
        for prj, spd in cfg.items():
            self.queues[prj].add(spd)

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
