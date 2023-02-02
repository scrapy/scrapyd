from integration_tests import req


def assert_webservice(method, path, expected, **kwargs):
    response = req(method, path, **kwargs)
    json = response.json()
    json.pop("node_name")

    assert json == expected


def test_listjobs():
    assert_webservice(
        "get",
        "/listjobs.json",
        {"status": "ok", "pending": [], "running": [], "finished": []},
    )


def test_listprojects():
    assert_webservice(
        "get",
        "/listprojects.json",
        {"status": "ok", "projects": []},
    )


def test_delproject_nonexistent():
    assert_webservice(
        "post",
        "/delproject.json",
        {"status": "error", "message": "[Errno 2] No such file or directory: 'eggs/nonexistent'"},
        data={"project": "nonexistent"},
    )
