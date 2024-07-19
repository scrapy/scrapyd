import pytest
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import IJobStorage
from scrapyd.jobstorage import Job, MemoryJobStorage, SqliteJobStorage

j1 = Job("p1", "s1")
j2 = Job("p2", "s2")
j3 = Job("p3", "s3")


@pytest.fixture()
def sqlitejobstorage(tmpdir):
    return SqliteJobStorage(Config(values={"dbs_dir": tmpdir, "finished_to_keep": "2"}))


@pytest.fixture()
def memoryjobstorage(tmpdir):
    storage = MemoryJobStorage(Config(values={"dbs_dir": tmpdir, "finished_to_keep": "2"}))
    storage.add(j1)
    storage.add(j2)
    storage.add(j3)
    return storage


def test_memory_interface(memoryjobstorage):
    verifyObject(IJobStorage, memoryjobstorage)


def test_memory_add(memoryjobstorage):
    assert len(memoryjobstorage.list()) == 2


def test_memory_iter(memoryjobstorage):
    actual = list(memoryjobstorage)

    assert actual[0] == j2
    assert actual[1] == j3
    assert len(actual) == 2


def test_len(memoryjobstorage):
    assert len(memoryjobstorage) == 2


def test_sqlite_interface(sqlitejobstorage):
    verifyObject(IJobStorage, sqlitejobstorage)


def test_sqlite_add(sqlitejobstorage):
    sqlitejobstorage.add(j1)
    sqlitejobstorage.add(j2)
    sqlitejobstorage.add(j3)

    assert len(sqlitejobstorage.list()) == 2


def test_sqlite_iter(sqlitejobstorage):
    sqlitejobstorage.add(j1)
    sqlitejobstorage.add(j2)
    sqlitejobstorage.add(j3)

    assert len(sqlitejobstorage) == 2
