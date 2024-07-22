import os.path
from pathlib import Path

import pytest
import requests

from integration_tests import req

BASEDIR = os.path.realpath(".").replace("\\", "\\\\")
with (Path(__file__).absolute().parent.parent / "tests" / "fixtures" / "quotesbot.egg").open("rb") as f:
    EGG = f.read()


def assert_webservice(method, path, expected, **kwargs):
    response = req(method, path, **kwargs)
    data = response.json()
    data.pop("node_name")

    assert data == expected


@pytest.mark.parametrize(
    ("webservice", "method"),
    [
        ("daemonstatus", "GET"),
        ("addversion", "POST"),
        ("schedule", "POST"),
        ("cancel", "POST"),
        ("status", "GET"),
        ("listprojects", "GET"),
        ("listversions", "GET"),
        ("listspiders", "GET"),
        ("listjobs", "GET"),
        ("delversion", "POST"),
        ("delproject", "POST"),
    ],
)
def test_options(webservice, method):
    response = requests.options(
        f"http://127.0.0.1:6800/{webservice}.json",
        auth=("hello12345", "67890world"),
    )

    assert response.status_code == 204, f"204 != {response.status_code}"
    assert response.content == b""
    assert response.headers["Allow"] == f"OPTIONS, HEAD, {method}"


# ListSpiders, Schedule, Cancel, Status and ListJobs return "project '%b' not found" on directory traversal attempts.
# The egg storage (in get_project_list, called by get_spider_queues, called by QueuePoller, used by these webservices)
# would need to find a project like "../project" (which is impossible with the default eggstorage) to not error.
@pytest.mark.parametrize(
    ("webservice", "method", "params"),
    [
        ("addversion", "post", {"version": "v", "egg": EGG}),
        ("listversions", "get", {}),
        ("delversion", "post", {"version": "v"}),
        ("delproject", "post", {}),
    ],
)
def test_project_directory_traversal(webservice, method, params):
    response = getattr(requests, method)(
        f"http://127.0.0.1:6800/{webservice}.json",
        auth=("hello12345", "67890world"),
        **{"params" if method == "get" else "data": {"project": "../p", **params}},
    )

    data = response.json()
    data.pop("node_name")

    assert response.status_code == 200, f"200 != {response.status_code}"
    assert data == {"status": "error", "message": "DirectoryTraversalError: ../p"}


def test_daemonstatus():
    assert_webservice("get", "/daemonstatus.json", {"status": "ok", "running": 0, "pending": 0, "finished": 0})


def test_schedule():
    assert_webservice(
        "post",
        "/schedule.json",
        {
            "status": "error",
            "message": "project 'nonexistent' not found",
        },
        data={"project": "nonexistent", "spider": "nospider"},
    )


def test_status_nonexistent_job():
    assert_webservice(
        "get",
        "/status.json",
        {"status": "ok", "currstate": None},
        params={"job": "sample"},
    )


def test_status_nonexistent_project():
    assert_webservice(
        "get",
        "/status.json",
        {"status": "error", "message": "project 'nonexistent' not found"},
        params={"job": "sample", "project": "nonexistent"},
    )


def test_cancel_nonexistent_project():
    assert_webservice(
        "post",
        "/cancel.json",
        {"status": "error", "message": "project 'nonexistent' not found"},
        data={"project": "nonexistent", "job": "nojob"},
    )


def test_listprojects():
    assert_webservice(
        "get",
        "/listprojects.json",
        {"status": "ok", "projects": []},
    )


def test_listversions():
    assert_webservice(
        "get",
        "/listversions.json",
        {"status": "ok", "versions": []},
        params={"project": "sample"},
    )


def test_listspiders_nonexistent_project():
    assert_webservice(
        "get",
        "/listspiders.json",
        {
            "status": "error",
            "message": "project 'nonexistent' not found",
        },
        params={"project": "nonexistent"},
    )


def test_listjobs():
    assert_webservice(
        "get",
        "/listjobs.json",
        {"status": "ok", "pending": [], "running": [], "finished": []},
    )


def test_listjobs_nonexistent_project():
    assert_webservice(
        "get",
        "/listjobs.json",
        {"status": "error", "message": "project 'nonexistent' not found"},
        params={"project": "nonexistent"},
    )


def test_delversion_nonexistent_project():
    assert_webservice(
        "post",
        "/delversion.json",
        {
            "status": "error",
            "message": "version 'nonexistent' not found",
        },
        data={"project": "sample", "version": "nonexistent"},
    )


def test_delproject_nonexistent_project():
    assert_webservice(
        "post",
        "/delproject.json",
        {
            "status": "error",
            "message": "project 'nonexistent' not found",
        },
        data={"project": "nonexistent"},
    )
