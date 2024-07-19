import os

import pytest
from twisted.internet.defer import Deferred
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import IPoller
from scrapyd.poller import QueuePoller
from scrapyd.utils import get_spider_queues


@pytest.fixture()
def poller(tmpdir):
    eggs_dir = os.path.join(tmpdir, "eggs")
    dbs_dir = os.path.join(tmpdir, "dbs")
    os.makedirs(os.path.join(eggs_dir, "mybot1"))
    os.makedirs(os.path.join(eggs_dir, "mybot2"))
    config = Config(values={"eggs_dir": eggs_dir, "dbs_dir": dbs_dir})
    return QueuePoller(config)


def test_interface(poller):
    verifyObject(IPoller, poller)


def test_poll_next(poller):
    queues = get_spider_queues(poller.config)

    cfg = {"mybot1": "spider1", "mybot2": "spider2"}
    priority = 0
    for prj, spd in cfg.items():
        queues[prj].add(spd, priority)

    d1 = poller.next()
    d2 = poller.next()

    assert isinstance(d1, Deferred)
    assert not hasattr(d1, "result")

    # poll once
    poller.poll()

    assert hasattr(d1, "result")
    assert getattr(d1, "called", False)

    # which project got run: project1 or project2?
    assert d1.result.get("_project")

    prj = d1.result["_project"]

    assert d1.result["_spider"] == cfg.pop(prj)

    queues[prj].pop()

    # poll twice
    # check that the other project's spider got to run
    poller.poll()
    prj, spd = cfg.popitem()

    assert d2.result == {"_project": prj, "_spider": spd}
