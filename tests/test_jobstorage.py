import datetime

from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import IJobStorage
from scrapyd.jobstorage import Job, MemoryJobStorage, SqliteJobStorage

j1 = Job("p1", "s1", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 7))
j2 = Job("p2", "s2", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 8))
j3 = Job("p3", "s3", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 9))


def pytest_generate_tests(metafunc):
    idlist = []
    argvalues = []
    for scenario, cls in metafunc.cls.scenarios:
        idlist.append(scenario)
        argnames = ["cls"]
        argvalues.append([cls])
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="class")


def config(tmpdir):
    return Config(values={"dbs_dir": tmpdir, "finished_to_keep": "2"})


class TestJobStorage:
    scenarios = (("sqlite", SqliteJobStorage), ("memory", MemoryJobStorage))

    def test_interface(self, cls, tmpdir):
        verifyObject(IJobStorage, cls(config(tmpdir)))

    def test_add(self, cls, tmpdir):
        jobstorage = cls(config(tmpdir))

        assert len(jobstorage) == 0

        jobstorage.add(j1)
        jobstorage.add(j2)
        jobstorage.add(j3)
        actual = jobstorage.list()

        assert len(jobstorage) == 2
        assert actual == list(jobstorage)
        assert actual == [j3, j2]

    def test_iter(self, cls, tmpdir):
        jobstorage = cls(config(tmpdir))

        assert len(jobstorage) == 0

        jobstorage.add(j1)
        jobstorage.add(j2)
        jobstorage.add(j3)
        actual = jobstorage.list()

        assert len(jobstorage) == 2
        assert actual == list(jobstorage)
        assert actual == [j3, j2]
