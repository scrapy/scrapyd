import scrapy

from integration_tests import req


def assert_webservice(method, path, expected, **kwargs):
    response = req(method, path, **kwargs)
    json = response.json()
    json.pop("node_name")

    assert json == expected


def test_daemonstatus():
    assert_webservice(
        "get",
        "/daemonstatus.json",
        {"status": "ok", "running": 0, "pending": 0, "finished": 0}
    )


def test_schedule():
    assert_webservice(
        "post",
        "/schedule.json",
        {
            "status": "error",
            "message": (
                f'Scrapy {scrapy.__version__} - no active project\n\n'
                'Unknown command: list\n\n'
                'Use "scrapy" to see available commands\n'
            ),
        },
        data={"project": "nonexistent", "spider": "nospider"},
    )


def test_cancel_nonexistent():
    assert_webservice(
        "post",
        "/cancel.json",
        {"status": "error", "message": "'nonexistent'"},
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


def test_listspiders_nonexistent():
    assert_webservice(
        "get",
        "/listspiders.json",
        {
            "status": "error",
            "message": (
                f'Scrapy {scrapy.__version__} - no active project\n\n'
                'Unknown command: list\n\n'
                'Use "scrapy" to see available commands\n'
            ),
        },
        params={"project": "nonexistent"},
    )


def test_listjobs():
    assert_webservice(
        "get",
        "/listjobs.json",
        {"status": "ok", "pending": [], "running": [], "finished": []},
    )


def test_delversion_nonexistent():
    assert_webservice(
        "post",
        "/delversion.json",
        {"status": "error", "message": "[Errno 2] No such file or directory: 'eggs/nonexistent/noegg.egg'"},
        data={"project": "nonexistent", "version": "noegg"},
    )


def test_delproject_nonexistent():
    assert_webservice(
        "post",
        "/delproject.json",
        {"status": "error", "message": "[Errno 2] No such file or directory: 'eggs/nonexistent'"},
        data={"project": "nonexistent"},
    )
