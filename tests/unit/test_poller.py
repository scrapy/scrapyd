import pytest
pytestmark = pytest.mark.unit

from pathlib import Path

import pytest
from twisted.internet.defer import Deferred
from zope.interface.verify import verifyObject

from scrapyd.config import Config
from scrapyd.interfaces import IPoller
from scrapyd.poller import QueuePoller
from scrapyd.utils import get_spider_queues


@pytest.fixture
def poller(tmpdir):
    eggs_dir = Path(tmpdir) / "eggs"
    dbs_dir = Path(tmpdir) / "dbs"
    config = Config(values={"eggs_dir": str(eggs_dir), "dbs_dir": str(dbs_dir)})
    (eggs_dir / "mybot1").mkdir(parents=True)
    (eggs_dir / "mybot2").mkdir(parents=True)
    return QueuePoller(config)


def test_interface(poller):
    verifyObject(IPoller, poller)


# Need sorted(), because os.listdir() in FilesystemEggStorage.list_projects() uses an arbitrary order.
def test_list_projects_update_projects(poller):
    assert sorted(poller.queues) == ["mybot1", "mybot2"]

    (Path(poller.config.get("eggs_dir")) / "settings_raise").mkdir(parents=True)

    assert sorted(poller.queues) == ["mybot1", "mybot2"]

    poller.update_projects()

    assert sorted(poller.queues) == ["mybot1", "mybot2", "settings_raise"]


def test_poll_next(poller):
    queues = get_spider_queues(poller.config)

    scenario = {"mybot1": "spider1", "mybot2": "spider2"}
    for project, spider in scenario.items():
        queues[project].add(spider)

    deferred1 = poller.next()
    deferred2 = poller.next()

    assert isinstance(deferred1, Deferred)
    assert not hasattr(deferred1, "result")
    assert isinstance(deferred2, Deferred)
    assert not hasattr(deferred2, "result")

    value = poller.poll()

    assert isinstance(value, Deferred)
    assert hasattr(value, "result")
    assert getattr(value, "called", False)
    assert value.result is None

    assert hasattr(deferred1, "result")
    assert getattr(deferred1, "called", False)
    assert hasattr(deferred2, "result")
    assert getattr(deferred2, "called", False)

    # os.listdir() in FilesystemEggStorage.list_projects() uses an arbitrary order.
    project_a = deferred1.result["_project"]
    spider_a = scenario.pop(project_a)
    project_b, spider_b = scenario.popitem()

    assert deferred1.result["_spider"] == spider_a
    assert deferred2.result == {"_project": project_b, "_spider": spider_b}


def test_poll_empty(poller):
    value = poller.poll()

    assert isinstance(value, Deferred)
    assert hasattr(value, "result")
    assert getattr(value, "called", False)
    assert value.result is None
