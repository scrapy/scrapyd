import pytest
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import ISpiderQueue
from scrapyd.spiderqueue import SqliteSpiderQueue

spider_args = {
    "arg1": "val1",
    "arg2": 2,
    "arg3": "\N{SNOWMAN}",
}
expected = spider_args.copy()
expected["name"] = "spider1"


@pytest.fixture()
def spiderqueue():
    return SqliteSpiderQueue(Config(values={"dbs_dir": ":memory:"}), "quotesbot")


def test_interface(spiderqueue):
    verifyObject(ISpiderQueue, spiderqueue)


@inlineCallbacks
def test_pop(spiderqueue):
    yield maybeDeferred(spiderqueue.add, "spider0", 5)
    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)
    yield maybeDeferred(spiderqueue.add, "spider1", 0)

    assert (yield maybeDeferred(spiderqueue.count)) == 3

    assert (yield maybeDeferred(spiderqueue.pop)) == expected

    assert (yield maybeDeferred(spiderqueue.count)) == 2


@inlineCallbacks
def test_list(spiderqueue):
    assert (yield maybeDeferred(spiderqueue.list)) == []

    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)
    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)

    assert (yield maybeDeferred(spiderqueue.list)) == [expected, expected]


@inlineCallbacks
def test_remove(spiderqueue):
    yield maybeDeferred(spiderqueue.add, "spider0", 5)
    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)
    yield maybeDeferred(spiderqueue.add, "spider1", 0)

    assert (yield maybeDeferred(spiderqueue.count)) == 3

    assert (yield maybeDeferred(spiderqueue.remove, lambda message: message["name"] == "spider1")) == 2

    assert (yield maybeDeferred(spiderqueue.count)) == 1


@inlineCallbacks
def test_clear(spiderqueue):
    assert (yield maybeDeferred(spiderqueue.count)) == 0

    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)
    yield maybeDeferred(spiderqueue.add, "spider1", 10, **spider_args)

    assert (yield maybeDeferred(spiderqueue.count)) == 2

    yield maybeDeferred(spiderqueue.clear)

    assert (yield maybeDeferred(spiderqueue.count)) == 0
