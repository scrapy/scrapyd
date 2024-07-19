import pytest
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from zope.interface.verify import verifyObject

from scrapyd import spiderqueue
from scrapyd.config import Config
from scrapyd.interfaces import ISpiderQueue

name = "spider1"
priority = 5
args = {
    "arg1": "val1",
    "arg2": 2,
    "arg3": "\N{SNOWMAN}",
}
expected = args.copy()
expected["name"] = name


@pytest.fixture()
def queue():
    return spiderqueue.SqliteSpiderQueue(Config(values={"dbs_dir": ":memory:"}), "quotesbot")


def test_interface(queue):
    verifyObject(ISpiderQueue, queue)


@inlineCallbacks
def test_add_pop_count(queue):
    c = yield maybeDeferred(queue.count)
    assert c == 0

    yield maybeDeferred(queue.add, name, priority, **args)

    c = yield maybeDeferred(queue.count)
    assert c == 1

    m = yield maybeDeferred(queue.pop)
    assert m == expected

    c = yield maybeDeferred(queue.count)
    assert c == 0


@inlineCallbacks
def test_list(queue):
    actual = yield maybeDeferred(queue.list)
    assert actual == []

    yield maybeDeferred(queue.add, name, priority, **args)
    yield maybeDeferred(queue.add, name, priority, **args)

    actual = yield maybeDeferred(queue.list)
    assert actual == [expected, expected]


@inlineCallbacks
def test_clear(queue):
    yield maybeDeferred(queue.add, name, priority, **args)
    yield maybeDeferred(queue.add, name, priority, **args)

    c = yield maybeDeferred(queue.count)
    assert c == 2

    yield maybeDeferred(queue.clear)

    c = yield maybeDeferred(queue.count)
    assert c == 0
