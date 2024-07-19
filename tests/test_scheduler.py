import os

import pytest
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import ISpiderScheduler
from scrapyd.scheduler import SpiderScheduler
from scrapyd.utils import get_spider_queues


@pytest.fixture()
def scheduler(tmpdir):
    eggs_dir = os.path.join(tmpdir, "eggs")
    dbs_dir = os.path.join(tmpdir, "dbs")
    os.makedirs(os.path.join(eggs_dir, "mybot1"))
    os.makedirs(os.path.join(eggs_dir, "mybot2"))
    config = Config(values={"eggs_dir": eggs_dir, "dbs_dir": dbs_dir})
    return SpiderScheduler(config)


def test_interface(scheduler):
    verifyObject(ISpiderScheduler, scheduler)


def test_list_update_projects(scheduler):
    assert sorted(scheduler.list_projects()) == sorted(["mybot1", "mybot2"])

    os.makedirs(os.path.join(scheduler.config.get("eggs_dir"), "mybot3"))
    scheduler.update_projects()

    assert sorted(scheduler.list_projects()) == sorted(["mybot1", "mybot2", "mybot3"])


def test_schedule(scheduler):
    queues = get_spider_queues(scheduler.config)
    q1, q2 = queues["mybot1"], queues["mybot2"]

    assert not q1.count()

    scheduler.schedule("mybot1", "myspider1", 2, a="b")
    scheduler.schedule("mybot2", "myspider2", 1, c="d")
    scheduler.schedule("mybot2", "myspider3", 10, e="f")

    assert q1.pop() == {"name": "myspider1", "a": "b"}
    assert q2.pop() == {"name": "myspider3", "e": "f"}
    assert q2.pop() == {"name": "myspider2", "c": "d"}
