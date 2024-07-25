import datetime

import pytest

from scrapyd.sqlite import JsonSqlitePriorityQueue, SqliteFinishedJobs
from tests import get_finished_job


@pytest.fixture()
def jsonsqlitepriorityqueue():
    return JsonSqlitePriorityQueue()


@pytest.fixture()
def sqlitefinishedjobs():
    q = SqliteFinishedJobs(":memory:")
    q.add(get_finished_job("p1", "s1", "j1", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 7)))
    q.add(get_finished_job("p2", "s2", "j2", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 8)))
    q.add(get_finished_job("p3", "s3", "j3", end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 9)))
    return q


def test_jsonsqlitepriorityqueue_empty(jsonsqlitepriorityqueue):
    assert jsonsqlitepriorityqueue.pop() is None


def test_jsonsqlitepriorityqueue_one(jsonsqlitepriorityqueue):
    msg = "a message"
    jsonsqlitepriorityqueue.put(msg)

    assert "_id" not in msg
    assert jsonsqlitepriorityqueue.pop() == msg
    assert jsonsqlitepriorityqueue.pop() is None


def test_jsonsqlitepriorityqueue_multiple(jsonsqlitepriorityqueue):
    msg1 = "first message"
    msg2 = "second message"
    jsonsqlitepriorityqueue.put(msg1)
    jsonsqlitepriorityqueue.put(msg2)
    out = []
    out.append(jsonsqlitepriorityqueue.pop())
    out.append(jsonsqlitepriorityqueue.pop())

    assert msg1 in out
    assert msg2 in out
    assert jsonsqlitepriorityqueue.pop() is None


def test_jsonsqlitepriorityqueue_priority(jsonsqlitepriorityqueue):
    msg1 = "message 1"
    msg2 = "message 2"
    msg3 = "message 3"
    msg4 = "message 4"
    jsonsqlitepriorityqueue.put(msg1, priority=1.0)
    jsonsqlitepriorityqueue.put(msg2, priority=5.0)
    jsonsqlitepriorityqueue.put(msg3, priority=3.0)
    jsonsqlitepriorityqueue.put(msg4, priority=2.0)

    assert jsonsqlitepriorityqueue.pop() == msg2
    assert jsonsqlitepriorityqueue.pop() == msg3
    assert jsonsqlitepriorityqueue.pop() == msg4
    assert jsonsqlitepriorityqueue.pop() == msg1


def test_jsonsqlitepriorityqueue_iter_len_clear(jsonsqlitepriorityqueue):
    assert len(jsonsqlitepriorityqueue) == 0
    assert list(jsonsqlitepriorityqueue) == []

    msg1 = "message 1"
    msg2 = "message 2"
    msg3 = "message 3"
    msg4 = "message 4"
    jsonsqlitepriorityqueue.put(msg1, priority=1.0)
    jsonsqlitepriorityqueue.put(msg2, priority=5.0)
    jsonsqlitepriorityqueue.put(msg3, priority=3.0)
    jsonsqlitepriorityqueue.put(msg4, priority=2.0)

    assert len(jsonsqlitepriorityqueue) == 4
    assert list(jsonsqlitepriorityqueue) == [(msg2, 5.0), (msg3, 3.0), (msg4, 2.0), (msg1, 1.0)]

    jsonsqlitepriorityqueue.clear()

    assert len(jsonsqlitepriorityqueue) == 0
    assert list(jsonsqlitepriorityqueue) == []


def test_jsonsqlitepriorityqueue_remove(jsonsqlitepriorityqueue):
    assert len(jsonsqlitepriorityqueue) == 0
    assert list(jsonsqlitepriorityqueue) == []

    msg1 = "good message 1"
    msg2 = "bad message 2"
    msg3 = "good message 3"
    msg4 = "bad message 4"
    jsonsqlitepriorityqueue.put(msg1)
    jsonsqlitepriorityqueue.put(msg2)
    jsonsqlitepriorityqueue.put(msg3)
    jsonsqlitepriorityqueue.put(msg4)
    jsonsqlitepriorityqueue.remove(lambda x: x.startswith("bad"))

    assert list(jsonsqlitepriorityqueue) == [(msg1, 0.0), (msg3, 0.0)]


@pytest.mark.parametrize(
    "value",
    [
        "native ascii str",
        "\xa3",
        123,
        1.2,
        True,
        ["a", "list", 1],
        {"a": "dict"},
    ],
)
def test_jsonsqlitepriorityqueue_types(jsonsqlitepriorityqueue, value):
    jsonsqlitepriorityqueue.put(value)

    assert jsonsqlitepriorityqueue.pop() == value


def test_sqlitefinishedjobs_add(sqlitefinishedjobs):
    assert len(sqlitefinishedjobs) == 3


def test_sqlitefinishedjobs_clear_all(sqlitefinishedjobs):
    sqlitefinishedjobs.clear()

    assert len(sqlitefinishedjobs) == 0


def test_sqlitefinishedjobs_clear_keep_2(sqlitefinishedjobs):
    sqlitefinishedjobs.clear(finished_to_keep=2)

    assert len(sqlitefinishedjobs) == 2


def test_sqlitefinishedjobs__iter__(sqlitefinishedjobs):
    actual = list(sqlitefinishedjobs)

    assert (actual[0][0], actual[0][1]) == ("p3", "s3")
    assert (actual[1][0], actual[1][1]) == ("p2", "s2")
    assert (actual[2][0], actual[2][1]) == ("p1", "s1")
