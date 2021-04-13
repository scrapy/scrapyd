import unittest
from datetime import datetime
from decimal import Decimal

from scrapy.http import Request
from scrapyd.sqlite import JsonSqlitePriorityQueue, JsonSqliteDict


class JsonSqliteDictTest(unittest.TestCase):

    dict_class = JsonSqliteDict
    test_dict = {'hello': 'world', 'int': 1, 'float': 1.5, 'null': None,
                 'list': ['a', 'word'], 'dict': {'some': 'dict'}}

    def test_basic_types(self):
        test = self.test_dict
        d = self.dict_class()
        d.update(test)
        self.assertEqual(list(d.items()), list(test.items()))
        d.clear()
        self.assertFalse(d.items())

    def test_in(self):
        d = self.dict_class()
        self.assertFalse('test' in d)
        d['test'] = 123
        self.assertTrue('test' in d)

    def test_keyerror(self):
        d = self.dict_class()
        self.assertRaises(KeyError, d.__getitem__, 'test')

    def test_replace(self):
        d = self.dict_class()
        self.assertEqual(d.get('test'), None)
        d['test'] = 123
        self.assertEqual(d.get('test'), 123)
        d['test'] = 456
        self.assertEqual(d.get('test'), 456)


class JsonSqlitePriorityQueueTest(unittest.TestCase):

    queue_class = JsonSqlitePriorityQueue

    supported_values = [
        "native ascii str",
        u"\xa3",
        123,
        1.2,
        True,
        ["a", "list", 1],
        {"a": "dict"},
    ]

    def setUp(self):
        self.q = self.queue_class()

    def test_empty(self):
        self.assertIs(self.q.pop(), None)

    def test_one(self):
        msg = "a message"
        self.q.put(msg)
        self.assertNotIn("_id", msg)
        self.assertEqual(self.q.pop(), msg)
        self.assertIs(self.q.pop(), None)

    def test_multiple(self):
        msg1 = "first message"
        msg2 = "second message"
        self.q.put(msg1)
        self.q.put(msg2)
        out = []
        out.append(self.q.pop())
        out.append(self.q.pop())
        self.assertIn(msg1, out)
        self.assertIn(msg2, out)
        self.assertIs(self.q.pop(), None)

    def test_priority(self):
        msg1 = "message 1"
        msg2 = "message 2"
        msg3 = "message 3"
        msg4 = "message 4"
        self.q.put(msg1, priority=1.0)
        self.q.put(msg2, priority=5.0)
        self.q.put(msg3, priority=3.0)
        self.q.put(msg4, priority=2.0)
        self.assertEqual(self.q.pop(), msg2)
        self.assertEqual(self.q.pop(), msg3)
        self.assertEqual(self.q.pop(), msg4)
        self.assertEqual(self.q.pop(), msg1)

    def test_iter_len_clear(self):
        self.assertEqual(len(self.q), 0)
        self.assertEqual(list(self.q), [])
        msg1 = "message 1"
        msg2 = "message 2"
        msg3 = "message 3"
        msg4 = "message 4"
        self.q.put(msg1, priority=1.0)
        self.q.put(msg2, priority=5.0)
        self.q.put(msg3, priority=3.0)
        self.q.put(msg4, priority=2.0)
        self.assertEqual(len(self.q), 4)
        self.assertEqual(list(self.q), \
            [(msg2, 5.0), (msg3, 3.0), (msg4, 2.0), (msg1, 1.0)])
        self.q.clear()
        self.assertEqual(len(self.q), 0)
        self.assertEqual(list(self.q), [])

    def test_remove(self):
        self.assertEqual(len(self.q), 0)
        self.assertEqual(list(self.q), [])
        msg1 = "good message 1"
        msg2 = "bad message 2"
        msg3 = "good message 3"
        msg4 = "bad message 4"
        self.q.put(msg1)
        self.q.put(msg2)
        self.q.put(msg3)
        self.q.put(msg4)
        self.q.remove(lambda x: x.startswith("bad"))
        self.assertEqual(list(self.q), [(msg1, 0.0), (msg3, 0.0)])

    def test_types(self):
        for x in self.supported_values:
            self.q.put(x)
            self.assertEqual(self.q.pop(), x)
