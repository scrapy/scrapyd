from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.trial import unittest

from zope.interface.verify import verifyObject

from scrapyd.interfaces import ISpiderQueue
from scrapyd import spiderqueue

class SpiderQueueTest(unittest.TestCase):
    """This test case also supports queues with deferred methods.
    """

    def setUp(self):
        self.q = spiderqueue.SqliteSpiderQueue(':memory:')
        self.name = 'spider1'
        self.priority = 5
        self.args = {
            'arg1': 'val1',
            'arg2': 2,
            'arg3': u'\N{SNOWMAN}',
        }
        self.msg = self.args.copy()
        self.msg['name'] = self.name


    def test_interface(self):
        verifyObject(ISpiderQueue, self.q)

    @inlineCallbacks
    def test_add_pop_count(self):
        c = yield maybeDeferred(self.q.count)
        self.assertEqual(c, 0)

        yield maybeDeferred(self.q.add, self.name, self.priority, **self.args)

        c = yield maybeDeferred(self.q.count)
        self.assertEqual(c, 1)

        m = yield maybeDeferred(self.q.pop)
        self.assertEqual(m, self.msg)

        c = yield maybeDeferred(self.q.count)
        self.assertEqual(c, 0)

    @inlineCallbacks
    def test_list(self):
        l = yield maybeDeferred(self.q.list)
        self.assertEqual(l, [])

        yield maybeDeferred(self.q.add, self.name, self.priority, **self.args)
        yield maybeDeferred(self.q.add, self.name, self.priority, **self.args)

        l = yield maybeDeferred(self.q.list)
        self.assertEqual(l, [self.msg, self.msg])

    @inlineCallbacks
    def test_clear(self):
        yield maybeDeferred(self.q.add, self.name, self.priority, **self.args)
        yield maybeDeferred(self.q.add, self.name, self.priority, **self.args)

        c = yield maybeDeferred(self.q.count)
        self.assertEqual(c, 2)

        yield maybeDeferred(self.q.clear)

        c = yield maybeDeferred(self.q.count)
        self.assertEqual(c, 0)
