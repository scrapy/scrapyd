import datetime
import io
import json
import os
import re
import sys
from unittest.mock import MagicMock, PropertyMock, call

import pytest
from twisted.logger import LogLevel, capturedLogs
from twisted.web import error

from scrapyd.exceptions import DirectoryTraversalError, RunnerError
from scrapyd.interfaces import IEggStorage
from scrapyd.launcher import ScrapyProcessProtocol
from scrapyd.webservice import spider_list
from tests import get_egg_data, get_finished_job, get_message, has_settings, root_add_version, touch

cliargs = [sys.executable, "-m", "scrapyd.runner", "crawl", "s2", "-s", "DOWNLOAD_DELAY=2", "-a", "arg1=val1"]

job1 = get_finished_job(
    project="p1",
    spider="s1",
    job="j1",
    start_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 7),
    end_time=datetime.datetime(2001, 2, 3, 4, 5, 6, 8),
)


@pytest.fixture()
def scrapy_process():
    process = ScrapyProcessProtocol(project="p1", spider="s1", job="j1", env={}, args=cliargs)
    process.start_time = datetime.datetime(2001, 2, 3, 4, 5, 6, 9)
    process.end_time = datetime.datetime(2001, 2, 3, 4, 5, 6, 10)
    process.transport = MagicMock()
    type(process.transport).pid = PropertyMock(return_value=12345)
    return process


def get_local_projects(root):
    return ["localproject"] if has_settings() else []


def add_test_version(app, project, version, basename):
    app.getComponent(IEggStorage).put(io.BytesIO(get_egg_data(basename)), project, version)


def assert_content(txrequest, root, method, basename, args, expected):
    txrequest.args = args.copy()
    txrequest.method = method
    content = root.children[b"%b.json" % basename.encode()].render(txrequest)
    data = json.loads(content)

    assert data.pop("node_name")
    assert data == {"status": "ok", **expected}


def assert_error(txrequest, root, method, basename, args, message):
    txrequest.args = args.copy()
    with pytest.raises(error.Error) as exc:
        getattr(root.children[b"%b.json" % basename.encode()], f"render_{method}")(txrequest)

    assert exc.value.status == b"200"
    assert exc.value.message == message


def test_spider_list(app):
    add_test_version(app, "myproject", "r1", "mybot")
    spiders = spider_list.get("myproject", None, runner="scrapyd.runner")
    assert sorted(spiders) == ["spider1", "spider2"]

    # Use the cache.
    add_test_version(app, "myproject", "r2", "mybot2")
    spiders = spider_list.get("myproject", None, runner="scrapyd.runner")
    assert sorted(spiders) == ["spider1", "spider2"]  # mybot2 has 3 spiders, but the cache wasn't evicted

    # Clear the cache.
    spider_list.delete("myproject")
    spiders = spider_list.get("myproject", None, runner="scrapyd.runner")
    assert sorted(spiders) == ["spider1", "spider2", "spider3"]

    # Re-add the 2-spider version and clear the cache.
    add_test_version(app, "myproject", "r3", "mybot")
    spider_list.delete("myproject")
    spiders = spider_list.get("myproject", None, runner="scrapyd.runner")
    assert sorted(spiders) == ["spider1", "spider2"]

    # Re-add the 3-spider version and clear the cache, but use a lower version number.
    add_test_version(app, "myproject", "r1a", "mybot2")
    spider_list.delete("myproject")
    spiders = spider_list.get("myproject", None, runner="scrapyd.runner")
    assert sorted(spiders) == ["spider1", "spider2"]


def test_spider_list_log_stdout(app):
    add_test_version(app, "logstdout", "logstdout", "logstdout")
    spiders = spider_list.get("logstdout", None, runner="scrapyd.runner")

    assert sorted(spiders) == ["spider1", "spider2"]  # [] if LOG_STDOUT were enabled


def test_spider_list_unicode(app):
    add_test_version(app, "myprojectunicode", "r1", "mybotunicode")
    spiders = spider_list.get("myprojectunicode", None, runner="scrapyd.runner")

    assert sorted(spiders) == ["araña1", "araña2"]


def test_spider_list_error(app):
    # mybot3.settings contains "raise Exception('This should break the `scrapy list` command')".
    add_test_version(app, "myproject3", "r1", "mybot3")
    with pytest.raises(RunnerError) as exc:
        spider_list.get("myproject3", None, runner="scrapyd.runner")

    assert re.search(f"Exception: This should break the `scrapy list` command{os.linesep}$", str(exc.value))


@pytest.mark.parametrize(
    ("method", "basename", "param", "args"),
    [
        ("POST", "schedule", "project", {}),
        ("POST", "schedule", "project", {b"spider": [b"scrapy-css"]}),
        ("POST", "schedule", "spider", {b"project": [b"quotesbot"]}),
        ("POST", "cancel", "project", {}),
        ("POST", "cancel", "project", {b"job": [b"aaa"]}),
        ("POST", "cancel", "job", {b"project": [b"quotesbot"]}),
        ("POST", "addversion", "project", {}),
        ("POST", "addversion", "project", {b"version": [b"0.1"]}),
        ("POST", "addversion", "version", {b"project": [b"quotesbot"]}),
        ("GET", "listversions", "project", {}),
        ("GET", "listspiders", "project", {}),
        ("GET", "status", "job", {}),
        ("POST", "delproject", "project", {}),
        ("POST", "delversion", "project", {}),
        ("POST", "delversion", "project", {b"version": [b"0.1"]}),
        ("POST", "delversion", "version", {b"project": [b"quotesbot"]}),
    ],
)
def test_required(txrequest, root_with_egg, method, basename, param, args):
    message = b"'%b' parameter is required" % param.encode()
    assert_error(txrequest, root_with_egg, method, basename, args, message)


def test_invalid_utf8(txrequest, root):
    args = {b"project": [b"\xc3\x28"]}
    message = b"project is invalid: 'utf-8' codec can't decode byte 0xc3 in position 0: invalid continuation byte"
    assert_error(txrequest, root, "GET", "listversions", args, message)


def test_invalid_type(txrequest, root):
    args = {b"project": [b"p"], b"spider": [b"s"], b"priority": [b"x"]}
    message = b"priority is invalid: could not convert string to float: b'x'"
    assert_error(txrequest, root, "POST", "schedule", args, message)


@pytest.mark.parametrize(
    ("method", "basename"),
    [
        ("GET", "daemonstatus"),
        ("POST", "addversion"),
        ("POST", "schedule"),
        ("POST", "cancel"),
        ("GET", "status"),
        ("GET", "listprojects"),
        ("GET", "listversions"),
        ("GET", "listspiders"),
        ("GET", "listjobs"),
        ("POST", "delversion"),
        ("POST", "delproject"),
    ],
)
def test_options(txrequest, root, method, basename):
    txrequest.method = "OPTIONS"

    content = root.children[b"%b.json" % basename.encode()].render(txrequest)
    expected = [b"OPTIONS, HEAD, %b" % method.encode()]

    assert txrequest.code == 204
    assert list(txrequest.responseHeaders.getAllRawHeaders()) == [
        (b"Allow", expected),
        (b"Access-Control-Allow-Origin", [b"*"]),
        (b"Access-Control-Allow-Methods", expected),
        (b"Access-Control-Allow-Headers", [b"X-Requested-With"]),
        (b"Content-Length", [b"0"]),
    ]
    assert content == b""


def test_debug(txrequest, root):
    root.debug = True

    txrequest.args = {b"project": [b"p"], b"spider": [b"s"], b"priority": [b"x"]}
    txrequest.method = "POST"

    with capturedLogs() as captured:
        response = root.children[b"schedule.json"].render(txrequest).decode()
    message = get_message(captured)

    assert txrequest.code == 200
    assert len(captured) == 1
    assert captured[0]["log_level"] == LogLevel.critical
    # The service is "scrapyd.webservice#critical" or "-" depending on whether twisted.python.log was loaded.
    assert re.search(r"^\[\S+\] \nTraceback \(most recent call last\):", message)
    assert message.endswith(
        "twisted.web.error.Error: 200 priority is invalid: could not convert string to float: b'x'\n"
    )
    assert response.startswith("Traceback (most recent call last):")
    assert response.endswith(
        "twisted.web.error.Error: 200 priority is invalid: could not convert string to float: b'x'\n"
    )


def test_daemonstatus(txrequest, root_with_egg, scrapy_process):
    expected = {"running": 0, "pending": 0, "finished": 0}
    assert_content(txrequest, root_with_egg, "GET", "daemonstatus", {}, expected)

    root_with_egg.launcher.finished.add(job1)
    expected["finished"] += 1
    assert_content(txrequest, root_with_egg, "GET", "daemonstatus", {}, expected)

    root_with_egg.launcher.processes[0] = scrapy_process
    expected["running"] += 1
    assert_content(txrequest, root_with_egg, "GET", "daemonstatus", {}, expected)

    root_with_egg.poller.queues["quotesbot"].add("quotesbot")
    expected["pending"] += 1
    assert_content(txrequest, root_with_egg, "GET", "daemonstatus", {}, expected)


@pytest.mark.parametrize(
    ("args", "spiders", "run_only_if_has_settings"),
    [
        ({b"project": [b"myproject"]}, ["spider1", "spider2", "spider3"], False),
        ({b"project": [b"myproject"], b"_version": [b"r1"]}, ["spider1", "spider2"], False),
        ({b"project": [b"localproject"]}, ["example"], True),
    ],
)
def test_list_spiders(txrequest, root, args, spiders, run_only_if_has_settings):
    if run_only_if_has_settings and not has_settings():
        pytest.skip("[settings] section is not set")

    root_add_version(root, "myproject", "r1", "mybot")
    root_add_version(root, "myproject", "r2", "mybot2")
    root.update_projects()

    expected = {"spiders": spiders}
    assert_content(txrequest, root, "GET", "listspiders", args, expected)


@pytest.mark.parametrize(
    ("args", "param", "run_only_if_has_settings"),
    [
        ({b"project": [b"nonexistent"]}, "project", False),
        ({b"project": [b"myproject"], b"_version": [b"nonexistent"]}, "version", False),
        ({b"project": [b"localproject"], b"_version": [b"nonexistent"]}, "version", True),
    ],
)
def test_list_spiders_nonexistent(txrequest, root, args, param, run_only_if_has_settings):
    if run_only_if_has_settings and not has_settings():
        pytest.skip("[settings] section is not set")

    root_add_version(root, "myproject", "r1", "mybot")
    root_add_version(root, "myproject", "r2", "mybot2")
    root.update_projects()

    assert_error(txrequest, root, "GET", "listspiders", args, b"%b 'nonexistent' not found" % param.encode())


def test_list_versions(txrequest, root_with_egg):
    expected = {"versions": ["0_1"]}
    assert_content(txrequest, root_with_egg, "GET", "listversions", {b"project": [b"quotesbot"]}, expected)


def test_list_versions_nonexistent(txrequest, root):
    expected = {"versions": []}
    assert_content(txrequest, root, "GET", "listversions", {b"project": [b"localproject"]}, expected)


def test_list_projects(txrequest, root_with_egg):
    expected = {"projects": ["quotesbot", *get_local_projects(root_with_egg)]}
    assert_content(txrequest, root_with_egg, "GET", "listprojects", {}, expected)


def test_list_projects_empty(txrequest, root):
    expected = {"projects": get_local_projects(root)}
    assert_content(txrequest, root, "GET", "listprojects", {}, expected)


@pytest.mark.parametrize("args", [{}, {b"project": [b"p1"]}])
def test_status(txrequest, root, scrapy_process, args):
    root_add_version(root, "p1", "r1", "mybot")
    root_add_version(root, "p2", "r2", "mybot2")
    root.update_projects()

    if args:
        root.launcher.finished.add(get_finished_job("p2", "s2", "j1"))
        root.launcher.processes[0] = ScrapyProcessProtocol("p2", "s2", "j1", env={}, args=[])
        root.poller.queues["p2"].add("s2", _job="j1")

    expected = {"currstate": None}
    assert_content(txrequest, root, "GET", "status", {b"job": [b"j1"], **args}, expected)

    root.poller.queues["p1"].add("s1", _job="j1")

    expected["currstate"] = "pending"
    assert_content(txrequest, root, "GET", "status", {b"job": [b"j1"], **args}, expected)

    root.launcher.processes[0] = scrapy_process

    expected["currstate"] = "running"
    assert_content(txrequest, root, "GET", "status", {b"job": [b"j1"], **args}, expected)

    root.launcher.finished.add(job1)

    expected["currstate"] = "finished"
    assert_content(txrequest, root, "GET", "status", {b"job": [b"j1"], **args}, expected)


def test_status_nonexistent(txrequest, root):
    args = {b"job": [b"aaa"], b"project": [b"nonexistent"]}
    assert_error(txrequest, root, "GET", "status", args, b"project 'nonexistent' not found")


@pytest.mark.parametrize("args", [{}, {b"project": [b"p1"]}])
@pytest.mark.parametrize("exists", [True, False])
def test_list_jobs(txrequest, root, scrapy_process, args, exists, chdir):
    root_add_version(root, "p1", "r1", "mybot")
    root_add_version(root, "p2", "r2", "mybot2")
    root.update_projects()

    if args:
        root.launcher.finished.add(get_finished_job("p2", "s2", "j2"))
        root.launcher.processes[0] = ScrapyProcessProtocol("p2", "s2", "j2", env={}, args=[])
        root.poller.queues["p2"].add("s2", _job="j2")

    if exists:
        touch(chdir / "logs" / "p1" / "s1" / "j1.log")
        touch(chdir / "items" / "p1" / "s1" / "j1.jl")

    expected = {"pending": [], "running": [], "finished": []}
    assert_content(txrequest, root, "GET", "listjobs", args, expected)

    root.launcher.finished.add(job1)

    expected["finished"].append(
        {
            "id": "j1",
            "project": "p1",
            "spider": "s1",
            "start_time": "2001-02-03 04:05:06.000007",
            "end_time": "2001-02-03 04:05:06.000008",
            "log_url": "/logs/p1/s1/j1.log" if exists else None,
            "items_url": "/items/p1/s1/j1.jl" if exists and root.local_items else None,
        },
    )
    assert_content(txrequest, root, "GET", "listjobs", args, expected)

    root.launcher.processes[0] = scrapy_process

    expected["running"].append(
        {
            "id": "j1",
            "project": "p1",
            "spider": "s1",
            "pid": None,
            "start_time": "2001-02-03 04:05:06.000009",
            "log_url": "/logs/p1/s1/j1.log" if exists else None,
            "items_url": "/items/p1/s1/j1.jl" if exists and root.local_items else None,
        }
    )
    assert_content(txrequest, root, "GET", "listjobs", args, expected)

    root.poller.queues["p1"].add(
        "s1",
        priority=5,
        _job="j1",
        _version="0.1",
        settings={"DOWNLOAD_DELAY=2": "TRACK=Cause = Time"},
        arg1="val1",
    )

    expected["pending"].append(
        {
            "id": "j1",
            "project": "p1",
            "spider": "s1",
            "version": "0.1",
            "settings": {"DOWNLOAD_DELAY=2": "TRACK=Cause = Time"},
            "args": {"arg1": "val1"},
        },
    )
    assert_content(txrequest, root, "GET", "listjobs", args, expected)


def test_list_jobs_nonexistent(txrequest, root):
    args = {b"project": [b"nonexistent"]}
    assert_error(txrequest, root, "GET", "listjobs", args, b"project 'nonexistent' not found")


def test_delete_version(txrequest, root):
    projects = get_local_projects(root)

    root_add_version(root, "myproject", "r1", "mybot")
    root_add_version(root, "myproject", "r2", "mybot2")
    root.update_projects()

    # Spiders (before).
    expected = {"spiders": ["spider1", "spider2", "spider3"]}
    assert_content(txrequest, root, "GET", "listspiders", {b"project": [b"myproject"]}, expected)

    # Delete one version.
    args = {b"project": [b"myproject"], b"version": [b"r2"]}
    assert_content(txrequest, root, "POST", "delversion", args, {"status": "ok"})
    assert root.eggstorage.get("myproject", "r2") == (None, None)  # version is gone

    # Spiders (after) would contain "spider3" without cache eviction.
    expected = {"spiders": ["spider1", "spider2"]}
    assert_content(txrequest, root, "GET", "listspiders", {b"project": [b"myproject"]}, expected)

    # Projects (before).
    assert_content(txrequest, root, "GET", "listprojects", {}, {"projects": ["myproject", *projects]})

    # Delete another version.
    args = {b"project": [b"myproject"], b"version": [b"r1"]}
    assert_content(txrequest, root, "POST", "delversion", args, {"status": "ok"})
    assert root.eggstorage.get("myproject") == (None, None)  # project is gone

    # Projects (after) would contain "myproject" without root.update_projects().
    assert_content(txrequest, root, "GET", "listprojects", {}, {"projects": [*projects]})


def test_delete_version_uncached(txrequest, root_with_egg):
    args = {b"project": [b"quotesbot"], b"version": [b"0.1"]}
    assert_content(txrequest, root_with_egg, "POST", "delversion", args, {"status": "ok"})


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({b"project": [b"quotesbot"], b"version": [b"nonexistent"]}, b"version 'nonexistent' not found"),
        ({b"project": [b"nonexistent"], b"version": [b"0.1"]}, b"version '0.1' not found"),
    ],
)
def test_delete_version_nonexistent(txrequest, root_with_egg, args, message):
    assert_error(txrequest, root_with_egg, "POST", "delversion", args, message)


def test_delete_project(txrequest, root_with_egg):
    projects = get_local_projects(root_with_egg)

    # Spiders (before).
    expected = {"spiders": ["toscrape-css", "toscrape-xpath"]}
    assert_content(txrequest, root_with_egg, "GET", "listspiders", {b"project": [b"quotesbot"]}, expected)

    # Projects (before).
    expected = {"projects": ["quotesbot", *projects]}
    assert_content(txrequest, root_with_egg, "GET", "listprojects", {}, expected)

    # Delete the project.
    args = {b"project": [b"quotesbot"]}
    assert_content(txrequest, root_with_egg, "POST", "delproject", args, {"status": "ok"})
    assert root_with_egg.eggstorage.get("quotesbot") == (None, None)  # project is gone

    # Spiders (after).
    args = {b"project": [b"quotesbot"]}
    assert_error(txrequest, root_with_egg, "GET", "listspiders", args, b"project 'quotesbot' not found")

    # Projects (after) would contain "quotesbot" without root.update_projects().
    expected = {"projects": [*projects]}
    assert_content(txrequest, root_with_egg, "GET", "listprojects", {}, expected)


def test_delete_project_uncached(txrequest, root_with_egg):
    args = {b"project": [b"quotesbot"]}
    assert_content(txrequest, root_with_egg, "POST", "delproject", args, {"status": "ok"})


def test_delete_project_nonexistent(txrequest, root):
    args = {b"project": [b"nonexistent"]}
    assert_error(txrequest, root, "POST", "delproject", args, b"project 'nonexistent' not found")


def test_add_version(txrequest, root):
    assert root.eggstorage.get("quotesbot") == (None, None)

    # Add a version.
    args = {b"project": [b"quotesbot"], b"version": [b"0.1"], b"egg": [get_egg_data("quotesbot")]}
    expected = {"project": "quotesbot", "version": "0.1", "spiders": 2}
    assert_content(txrequest, root, "POST", "addversion", args, expected)
    assert root.eggstorage.list("quotesbot") == ["0_1"]

    # Spiders (before).
    expected = {"spiders": ["toscrape-css", "toscrape-xpath"]}
    assert_content(txrequest, root, "GET", "listspiders", {b"project": [b"quotesbot"]}, expected)

    # Add the same version with a different egg.
    args = {b"project": [b"quotesbot"], b"version": [b"0.1"], b"egg": [get_egg_data("mybot2")]}
    expected = {"project": "quotesbot", "version": "0.1", "spiders": 3}  # 2 without cache eviction
    assert_content(txrequest, root, "POST", "addversion", args, expected)
    assert root.eggstorage.list("quotesbot") == ["0_1"]  # overwrite version

    # Spiders (after).
    expected = {"spiders": ["spider1", "spider2", "spider3"]}
    assert_content(txrequest, root, "GET", "listspiders", {b"project": [b"quotesbot"]}, expected)


def test_add_version_settings(txrequest, root):
    if not has_settings():
        pytest.skip("[settings] section is not set")

    args = {b"project": [b"localproject"], b"version": [b"0.1"], b"egg": [get_egg_data("quotesbot")]}
    expected = {"project": "localproject", "spiders": 2, "version": "0.1"}
    assert_content(txrequest, root, "POST", "addversion", args, expected)


def test_add_version_invalid(txrequest, root):
    args = {b"project": [b"quotesbot"], b"version": [b"0.1"], b"egg": [b"invalid"]}
    message = b"egg is not a ZIP file (if using curl, use egg=@path not egg=path)"
    assert_error(txrequest, root, "POST", "addversion", args, message)


# Like test_list_spiders.
@pytest.mark.parametrize(
    ("args", "run_only_if_has_settings"),
    [
        ({b"project": [b"myproject"], b"spider": [b"spider3"]}, False),
        ({b"project": [b"myproject"], b"_version": [b"r1"], b"spider": [b"spider1"]}, False),
        ({b"project": [b"localproject"], b"spider": [b"example"]}, True),
    ],
)
def test_schedule(txrequest, root, args, run_only_if_has_settings):
    if run_only_if_has_settings and not has_settings():
        pytest.skip("[settings] section is not set")

    project = args[b"project"][0].decode()
    spider = args[b"spider"][0].decode()
    version = args[b"_version"][0].decode() if b"_version" in args else None

    root_add_version(root, "myproject", "r1", "mybot")
    root_add_version(root, "myproject", "r2", "mybot2")
    root.update_projects()

    assert root.poller.queues[project].list() == []

    txrequest.args = args.copy()
    txrequest.method = "POST"
    content = root.children[b"schedule.json"].render(txrequest)
    data = json.loads(content)
    jobid = data.pop("jobid")

    assert data.pop("node_name")
    assert data == {"status": "ok"}
    assert re.search(r"^[a-z0-9]{32}$", jobid)

    jobs = root.poller.queues[project].list()
    expected = {"name": spider, "_job": jobid, "settings": {}}
    if version:
        expected["_version"] = version

    assert len(jobs) == 1
    assert jobs[0] == expected


def test_schedule_unique(txrequest, root_with_egg):
    args = {b"project": [b"quotesbot"], b"spider": [b"toscrape-css"]}
    txrequest.method = "POST"

    txrequest.args = args.copy()
    content = root_with_egg.children[b"schedule.json"].render(txrequest)
    data = json.loads(content)

    jobid = data.pop("jobid")

    txrequest.args = args.copy()
    content = root_with_egg.children[b"schedule.json"].render(txrequest)
    data = json.loads(content)

    assert data.pop("jobid") != jobid


def test_schedule_parameters(txrequest, root_with_egg):
    txrequest.args = {
        b"project": [b"quotesbot"],
        b"spider": [b"toscrape-css"],
        b"_version": [b"0.1"],
        b"jobid": [b"aaa"],
        b"priority": [b"5"],
        b"setting": [b"DOWNLOAD_DELAY=2", b"TRACK=Cause = Time"],
        b"arg1": [b"val1", b"val2"],
    }
    txrequest.method = "POST"
    content = root_with_egg.children[b"schedule.json"].render(txrequest)
    data = json.loads(content)

    assert data.pop("node_name")
    assert data == {"status": "ok", "jobid": "aaa"}

    jobs = root_with_egg.poller.queues["quotesbot"].list()

    assert len(jobs) == 1
    assert jobs[0] == {
        "name": "toscrape-css",
        "_version": "0.1",
        "_job": "aaa",
        "settings": {
            "DOWNLOAD_DELAY": "2",
            "TRACK": "Cause = Time",
        },
        "arg1": "val1",  # users are encouraged in api.rst to open an issue if they want multiple values
    }


# Like test_list_spiders_nonexistent.
@pytest.mark.parametrize(
    ("args", "param", "run_only_if_has_settings"),
    [
        ({b"project": [b"nonexistent"], b"spider": [b"spider1"]}, "project", False),
        ({b"project": [b"myproject"], b"_version": [b"nonexistent"], b"spider": [b"spider1"]}, "version", False),
        ({b"project": [b"myproject"], b"spider": [b"nonexistent"]}, "spider", False),
        ({b"project": [b"localproject"], b"_version": [b"nonexistent"], b"spider": [b"example"]}, "version", True),
    ],
)
def test_schedule_nonexistent(txrequest, root, args, param, run_only_if_has_settings):
    if run_only_if_has_settings and not has_settings():
        pytest.skip("[settings] section is not set")

    root_add_version(root, "myproject", "r1", "mybot")
    root_add_version(root, "myproject", "r2", "mybot2")
    root.update_projects()

    assert_error(txrequest, root, "POST", "schedule", args, b"%b 'nonexistent' not found" % param.encode())


@pytest.mark.parametrize("args", [{}, {b"signal": [b"TERM"]}])
def test_cancel(txrequest, root, scrapy_process, args):
    signal = "TERM" if args else ("INT" if sys.platform != "win32" else "BREAK")

    root_add_version(root, "p1", "r1", "mybot")
    root_add_version(root, "p2", "r2", "mybot2")
    root.update_projects()

    args = {b"project": [b"p1"], b"job": [b"j1"], **args}

    expected = {"prevstate": None}
    assert_content(txrequest, root, "POST", "cancel", args, expected)

    root.poller.queues["p1"].add("s1", _job="j1")
    root.poller.queues["p1"].add("s1", _job="j1")
    root.poller.queues["p1"].add("s1", _job="j2")

    assert root.poller.queues["p1"].count() == 3
    expected["prevstate"] = "pending"
    assert_content(txrequest, root, "POST", "cancel", args, expected)
    assert root.poller.queues["p1"].count() == 1

    root.launcher.processes[0] = scrapy_process
    root.launcher.processes[1] = scrapy_process
    root.launcher.processes[2] = ScrapyProcessProtocol("p2", "s2", "j2", env={}, args=[])

    expected["prevstate"] = "running"
    assert_content(txrequest, root, "POST", "cancel", args, expected)
    assert scrapy_process.transport.signalProcess.call_count == 2
    scrapy_process.transport.signalProcess.assert_has_calls([call(signal), call(signal)])


def test_cancel_nonexistent(txrequest, root):
    args = {b"project": [b"nonexistent"], b"job": [b"aaa"]}
    assert_error(txrequest, root, "POST", "cancel", args, b"project 'nonexistent' not found")


# ListSpiders, Schedule, Cancel, Status and ListJobs return "project '%b' not found" on directory traversal attempts.
# The egg storage (in get_project_list, called by get_spider_queues, called by QueuePoller, used by these webservices)
# would need to find a project like "../project" (which is impossible with the default eggstorage) to not error.
@pytest.mark.parametrize(
    ("method", "basename", "args"),
    [
        ("POST", "cancel", {b"project": [b"../p"], b"job": [b"aaa"]}),
        ("GET", "status", {b"project": [b"../p"], b"job": [b"aaa"]}),
        ("GET", "listspiders", {b"project": [b"../p"]}),
        ("GET", "listjobs", {b"project": [b"../p"]}),
    ],
)
def test_project_directory_traversal_notfound(txrequest, root, method, basename, args):
    assert_error(txrequest, root, method, basename, args, b"project '../p' not found")


@pytest.mark.parametrize(
    ("method", "basename", "attach_egg"),
    [
        ("POST", "addversion", True),
        ("GET", "listversions", False),
        ("POST", "delproject", False),
        ("POST", "delversion", False),
    ],
)
def test_project_directory_traversal(txrequest, root, method, basename, attach_egg):
    txrequest.args = {b"project": [b"../p"], b"version": [b"0.1"]}

    if attach_egg:
        txrequest.args[b"egg"] = [get_egg_data("quotesbot")]

    with pytest.raises(DirectoryTraversalError) as exc:
        getattr(root.children[b"%b.json" % basename.encode()], f"render_{method}")(txrequest)

    assert str(exc.value) == "../p"

    eggstorage = root.app.getComponent(IEggStorage)
    assert eggstorage.get("quotesbot") == (None, None)
