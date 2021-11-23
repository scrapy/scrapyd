from twisted.trial import unittest

from zope.interface.verify import verifyObject

from scrapyd.interfaces import IJobStorage
from scrapyd.config import Config
from scrapyd.jobstorage import Job, MemoryJobStorage, SqliteJobStorage

j1, j2, j3 = Job('p1', 's1'), Job('p2', 's2'), Job('p3', 's3')


class MemoryJobStorageTest(unittest.TestCase):

    def setUp(self):
        d = self.mktemp()
        config = Config(values={'dbs_dir': d, 'finished_to_keep': '2'})
        self.jobst = MemoryJobStorage(config)
        self.j1, self.j2, self.j3 = j1, j2, j3
        self.jobst.add(self.j1)
        self.jobst.add(self.j2)
        self.jobst.add(self.j3)

    def test_interface(self):
        verifyObject(IJobStorage, self.jobst)

    def test_add(self):
        self.assertEqual(len(self.jobst.list()), 2)

    def test_iter(self):
        l = [j for j in self.jobst]
        self.assertEqual(l[0], j2)
        self.assertEqual(l[1], j3)
        self.assertEqual(len(l), 2)

    def test_len(self):
        self.assertEqual(len(self.jobst), 2)


class SqliteJobsStorageTest(unittest.TestCase):

    def setUp(self):
        d = self.mktemp()
        config = Config(values={'dbs_dir': d, 'finished_to_keep': '2'})
        self.jobst = SqliteJobStorage(config)
        self.j1, self.j2, self.j3 = j1, j2, j3

    def test_interface(self):
        verifyObject(IJobStorage, self.jobst)

    def test_add(self):
        self.jobst.add(self.j1)
        self.jobst.add(self.j2)
        self.jobst.add(self.j3)
        self.assertEqual(len(self.jobst.list()), 2)

    def test_iter(self):
        self.jobst.add(self.j1)
        self.jobst.add(self.j2)
        self.jobst.add(self.j3)
        l = [j for j in self.jobst]
        self.assertEqual(len(l), 2)
