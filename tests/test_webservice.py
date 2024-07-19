import io
import os
import re
from unittest import mock

import pytest
from scrapy.utils.test import get_pythonpath
from twisted.web import error

from scrapyd import get_application
from scrapyd.exceptions import DirectoryTraversalError, RunnerError
from scrapyd.interfaces import IEggStorage
from scrapyd.jobstorage import Job
from scrapyd.webservice import UtilsCache, get_spider_list
from tests import get_egg_data, root_add_version


def fake_list_jobs(*args, **kwargs):
    yield Job("proj1", "spider-a", "id1234")


def fake_list_spiders(*args, **kwargs):
    return []


def fake_list_spiders_other(*args, **kwargs):
    return ["quotesbot", "toscrape-css"]


def get_pythonpath_scrapyd():
    scrapyd_path = __import__("scrapyd").__path__[0]
    return os.path.join(os.path.dirname(scrapyd_path), get_pythonpath(), os.environ.get("PYTHONPATH", ""))


@pytest.fixture()
def app():
    return get_application()


def add_test_version(app, project, version, basename):
    app.getComponent(IEggStorage).put(io.BytesIO(get_egg_data(basename)), project, version)


def test_get_spider_list_log_stdout(app):
    add_test_version(app, "logstdout", "logstdout", "logstdout")
    spiders = get_spider_list("logstdout", pythonpath=get_pythonpath_scrapyd())

    # If LOG_STDOUT were respected, the output would be [].
    assert sorted(spiders) == ["spider1", "spider2"]


def test_get_spider_list(app):
    # mybot.egg has two spiders, spider1 and spider2
    add_test_version(app, "mybot", "r1", "mybot")
    spiders = get_spider_list("mybot", pythonpath=get_pythonpath_scrapyd())
    assert sorted(spiders) == ["spider1", "spider2"]

    # mybot2.egg has three spiders, spider1, spider2 and spider3...
    # BUT you won't see it here because it's cached.
    # Effectivelly it's like if version was never added
    add_test_version(app, "mybot", "r2", "mybot2")
    spiders = get_spider_list("mybot", pythonpath=get_pythonpath_scrapyd())
    assert sorted(spiders) == ["spider1", "spider2"]

    # Let's invalidate the cache for this project...
    UtilsCache.invalid_cache("mybot")

    # Now you get the updated list
    spiders = get_spider_list("mybot", pythonpath=get_pythonpath_scrapyd())
    assert sorted(spiders) == ["spider1", "spider2", "spider3"]

    # Let's re-deploy mybot.egg and clear cache. It now sees 2 spiders
    add_test_version(app, "mybot", "r3", "mybot")
    UtilsCache.invalid_cache("mybot")
    spiders = get_spider_list("mybot", pythonpath=get_pythonpath_scrapyd())
    assert sorted(spiders) == ["spider1", "spider2"]

    # And re-deploying the one with three (mybot2.egg) with a version that
    # isn't the higher, won't change what get_spider_list() returns.
    add_test_version(app, "mybot", "r1a", "mybot2")
    UtilsCache.invalid_cache("mybot")
    spiders = get_spider_list("mybot", pythonpath=get_pythonpath_scrapyd())
    assert sorted(spiders) == ["spider1", "spider2"]


@pytest.mark.skipif(os.name == "nt", reason="get_spider_list() unicode fails on windows")
def test_get_spider_list_unicode(app):
    # mybotunicode.egg has two spiders, araña1 and araña2
    add_test_version(app, "mybotunicode", "r1", "mybotunicode")
    spiders = get_spider_list("mybotunicode", pythonpath=get_pythonpath_scrapyd())

    assert sorted(spiders) == ["araña1", "araña2"]


def test_failed_spider_list(app):
    add_test_version(app, "mybot3", "r1", "mybot3")
    with pytest.raises(RunnerError) as exc:
        get_spider_list("mybot3", pythonpath=get_pythonpath_scrapyd())

    assert re.search(f"Exception: This should break the `scrapy list` command{os.linesep}$", str(exc.value))


def test_list_spiders(txrequest, site_no_egg):
    root_add_version(site_no_egg, "myproject", "r1", "mybot")
    root_add_version(site_no_egg, "myproject", "r2", "mybot2")

    txrequest.args = {b"project": [b"myproject"]}
    endpoint = b"listspiders.json"
    content = site_no_egg.children[endpoint].render_GET(txrequest)

    assert content["spiders"] == ["spider1", "spider2", "spider3"]
    assert content["status"] == "ok"


def test_list_spiders_nonexistent(txrequest, site_no_egg):
    txrequest.args = {
        b"project": [b"nonexistent"],
    }
    endpoint = b"listspiders.json"

    with pytest.raises(error.Error) as exc:
        site_no_egg.children[endpoint].render_GET(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"project 'nonexistent' not found"


def test_list_spiders_version(txrequest, site_no_egg):
    root_add_version(site_no_egg, "myproject", "r1", "mybot")
    root_add_version(site_no_egg, "myproject", "r2", "mybot2")

    txrequest.args = {
        b"project": [b"myproject"],
        b"_version": [b"r1"],
    }
    endpoint = b"listspiders.json"
    content = site_no_egg.children[endpoint].render_GET(txrequest)

    assert content["spiders"] == ["spider1", "spider2"]
    assert content["status"] == "ok"


def test_list_spiders_version_nonexistent(txrequest, site_no_egg):
    root_add_version(site_no_egg, "myproject", "r1", "mybot")
    root_add_version(site_no_egg, "myproject", "r2", "mybot2")

    txrequest.args = {
        b"project": [b"myproject"],
        b"_version": [b"nonexistent"],
    }
    endpoint = b"listspiders.json"

    with pytest.raises(error.Error) as exc:
        site_no_egg.children[endpoint].render_GET(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"version 'nonexistent' not found"


def test_list_versions(txrequest, site_with_egg):
    txrequest.args = {
        b"project": [b"quotesbot"],
    }
    endpoint = b"listversions.json"
    content = site_with_egg.children[endpoint].render_GET(txrequest)

    assert content["versions"] == ["0_1"]
    assert content["status"] == "ok"


def test_list_versions_nonexistent(txrequest, site_no_egg):
    txrequest.args = {
        b"project": [b"quotesbot"],
    }
    endpoint = b"listversions.json"
    content = site_no_egg.children[endpoint].render_GET(txrequest)

    assert content["versions"] == []
    assert content["status"] == "ok"


def test_list_projects(txrequest, site_with_egg):
    txrequest.args = {b"project": [b"quotesbot"], b"spider": [b"toscrape-css"]}
    endpoint = b"listprojects.json"
    content = site_with_egg.children[endpoint].render_GET(txrequest)

    assert content["projects"] == ["quotesbot"]


def test_list_jobs(txrequest, site_with_egg):
    txrequest.args = {}
    endpoint = b"listjobs.json"
    content = site_with_egg.children[endpoint].render_GET(txrequest)

    assert set(content) == {"node_name", "status", "pending", "running", "finished"}


@mock.patch("scrapyd.jobstorage.MemoryJobStorage.__iter__", new=fake_list_jobs)
def test_list_jobs_finished(txrequest, site_with_egg):
    txrequest.args = {}
    endpoint = b"listjobs.json"
    content = site_with_egg.children[endpoint].render_GET(txrequest)

    assert set(content["finished"][0]) == {
        "project",
        "spider",
        "id",
        "start_time",
        "end_time",
        "log_url",
        "items_url",
    }


def test_delete_version(txrequest, site_with_egg):
    endpoint = b"delversion.json"
    txrequest.args = {b"project": [b"quotesbot"], b"version": [b"0.1"]}

    storage = site_with_egg.app.getComponent(IEggStorage)
    version, egg = storage.get("quotesbot")
    if egg:
        egg.close()

    content = site_with_egg.children[endpoint].render_POST(txrequest)
    no_version, no_egg = storage.get("quotesbot")
    if no_egg:
        no_egg.close()

    assert version is not None
    assert content["status"] == "ok"
    assert "node_name" in content
    assert no_version is None


def test_delete_version_nonexistent_project(txrequest, site_with_egg):
    endpoint = b"delversion.json"
    txrequest.args = {b"project": [b"quotesbot"], b"version": [b"nonexistent"]}

    with pytest.raises(error.Error) as exc:
        site_with_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"version 'nonexistent' not found"


def test_delete_version_nonexistent_version(txrequest, site_no_egg):
    endpoint = b"delversion.json"
    txrequest.args = {b"project": [b"nonexistent"], b"version": [b"0.1"]}

    with pytest.raises(error.Error) as exc:
        site_no_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"version '0.1' not found"


def test_delete_project(txrequest, site_with_egg):
    endpoint = b"delproject.json"
    txrequest.args = {
        b"project": [b"quotesbot"],
    }

    storage = site_with_egg.app.getComponent(IEggStorage)
    version, egg = storage.get("quotesbot")
    if egg:
        egg.close()

    content = site_with_egg.children[endpoint].render_POST(txrequest)
    no_version, no_egg = storage.get("quotesbot")
    if no_egg:
        no_egg.close()

    assert version is not None
    assert content["status"] == "ok"
    assert "node_name" in content
    assert no_version is None


def test_delete_project_nonexistent(txrequest, site_no_egg):
    endpoint = b"delproject.json"
    txrequest.args = {
        b"project": [b"nonexistent"],
    }

    with pytest.raises(error.Error) as exc:
        site_no_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"project 'nonexistent' not found"


def test_addversion(txrequest, site_no_egg):
    endpoint = b"addversion.json"
    txrequest.args = {b"project": [b"quotesbot"], b"version": [b"0.1"]}
    txrequest.args[b"egg"] = [get_egg_data("quotesbot")]

    storage = site_no_egg.app.getComponent(IEggStorage)
    version, egg = storage.get("quotesbot")
    if egg:
        egg.close()

    content = site_no_egg.children[endpoint].render_POST(txrequest)
    no_version, no_egg = storage.get("quotesbot")
    if no_egg:
        no_egg.close()

    assert version is None
    assert content["status"] == "ok"
    assert "node_name" in content
    assert no_version == "0_1"


def test_schedule(txrequest, site_with_egg):
    endpoint = b"schedule.json"
    txrequest.args = {b"project": [b"quotesbot"], b"spider": [b"toscrape-css"]}

    content = site_with_egg.children[endpoint].render_POST(txrequest)

    assert site_with_egg.scheduler.calls == [["quotesbot", "toscrape-css"]]
    assert content["status"] == "ok"
    assert "jobid" in content


def test_schedule_nonexistent_project(txrequest, site_no_egg):
    endpoint = b"schedule.json"
    txrequest.args = {b"project": [b"nonexistent"], b"spider": [b"toscrape-css"]}

    with pytest.raises(error.Error) as exc:
        site_no_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"project 'nonexistent' not found"


def test_schedule_nonexistent_version(txrequest, site_with_egg):
    endpoint = b"schedule.json"
    txrequest.args = {b"project": [b"quotesbot"], b"_version": [b"nonexistent"], b"spider": [b"toscrape-css"]}

    with pytest.raises(error.Error) as exc:
        site_with_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"version 'nonexistent' not found"


def test_schedule_nonexistent_spider(txrequest, site_with_egg):
    endpoint = b"schedule.json"
    txrequest.args = {b"project": [b"quotesbot"], b"spider": [b"nonexistent"]}

    with pytest.raises(error.Error) as exc:
        site_with_egg.children[endpoint].render_POST(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == b"spider 'nonexistent' not found"


@pytest.mark.parametrize(
    ("endpoint", "attach_egg", "method"),
    [
        (b"addversion.json", True, "render_POST"),
        (b"listversions.json", False, "render_GET"),
        (b"delproject.json", False, "render_POST"),
        (b"delversion.json", False, "render_POST"),
    ],
)
def test_project_directory_traversal(txrequest, site_no_egg, endpoint, attach_egg, method):
    txrequest.args = {
        b"project": [b"../p"],
        b"version": [b"0.1"],
    }

    if attach_egg:
        txrequest.args[b"egg"] = [get_egg_data("quotesbot")]

    with pytest.raises(DirectoryTraversalError) as exc:
        getattr(site_no_egg.children[endpoint], method)(txrequest)

    assert str(exc.value) == "../p"

    storage = site_no_egg.app.getComponent(IEggStorage)
    version, egg = storage.get("quotesbot")
    if egg:
        egg.close()

    assert version is None


@pytest.mark.parametrize(
    ("endpoint", "attach_egg", "method"),
    [
        (b"schedule.json", False, "render_POST"),
        (b"listspiders.json", False, "render_GET"),
    ],
)
def test_project_directory_traversal_runner(txrequest, site_no_egg, endpoint, attach_egg, method):
    txrequest.args = {
        b"project": [b"../p"],
        b"spider": [b"s"],
    }

    if attach_egg:
        txrequest.args[b"egg"] = [get_egg_data("quotesbot")]

    with pytest.raises(DirectoryTraversalError) as exc:
        getattr(site_no_egg.children[endpoint], method)(txrequest)

    assert str(exc.value) == "../p"

    storage = site_no_egg.app.getComponent(IEggStorage)
    version, egg = storage.get("quotesbot")
    if egg:
        egg.close()

    assert version is None
