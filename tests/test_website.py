import os

import pytest
from html_checker.validator import ValidatorInterface
from twisted.web import http_headers, resource
from twisted.web.test._util import _render
from twisted.web.test.requesthelper import DummyRequest

from scrapyd.app import application
from scrapyd.launcher import ScrapyProcessProtocol
from scrapyd.website import Root
from tests import get_finished_job, has_settings, root_add_version, touch


def assert_headers(txrequest):
    headers = dict(txrequest.responseHeaders.getAllRawHeaders())
    content_length = headers.pop(b"Content-Length")

    assert len(content_length) == 1
    assert isinstance(content_length[0], bytes)
    assert int(content_length[0])
    assert headers == {b"Content-Type": [b"text/html; charset=utf-8"]}


def assert_hrefs(urls, text, header):
    for href, name in urls:
        if header:
            assert f'<a href="/path/to/{href}">{name}</a>' in text
        else:
            assert f'<a href="/{href}">{name}</a>' in text


# Derived from test_emptyChildUnicodeParent.
# https://github.com/twisted/twisted/blob/trunk/src/twisted/web/test/test_static.py
def test_logs_dir(txrequest, root):
    os.makedirs(os.path.join("logs", "quotesbot"))

    file = root.children[b"logs"]
    request = DummyRequest([b""])
    child = resource.getChildForRequest(file, request)

    content = child.render(request)

    assert list(request.responseHeaders.getAllRawHeaders()) == [(b"Content-Type", [b"text/html; charset=utf-8"])]
    assert b"<th>Last modified</th>" in content
    assert b'<td><a href="quotesbot/">quotesbot/</a></td>' in content


# Derived from test_indexNames.
# https://github.com/twisted/twisted/blob/trunk/src/twisted/web/test/test_static.py
def test_logs_file(txrequest, root):
    os.makedirs(os.path.join("logs", "quotesbot"))
    with open(os.path.join("logs", "foo.txt"), "wb") as f:
        f.write(b"baz")

    file = root.children[b"logs"]
    request = DummyRequest([b"foo.txt"])
    child = resource.getChildForRequest(file, request)

    d = _render(child, request)

    def cbRendered(ignored):
        assert list(request.responseHeaders.getAllRawHeaders()) == [
            (b"Accept-Ranges", [b"bytes"]),
            (b"Content-Length", [b"3"]),
            (b"Content-Type", [b"text/plain"]),
        ]
        assert b"".join(request.written) == b"baz"

    d.addCallback(cbRendered)
    return d


@pytest.mark.parametrize("cancel", [True, False], ids=["cancel", "no_cancel"])
@pytest.mark.parametrize("header", [True, False], ids=["header", "no_header"])
@pytest.mark.parametrize("exists", [True, False], ids=["exists", "no_exists"])
def test_jobs(txrequest, config, cancel, header, exists, chdir):
    if not cancel:
        config.cp.remove_option("services", "cancel.json")

    root = Root(config, application(config))
    root_add_version(root, "quotesbot", "0.1", "quotesbot")
    root.update_projects()

    urls = [
        ("logs/p1/s1/j1-finished.log", "Log"),
        ("logs/p2/s2/j2-running.log", "Log"),
        ("logs/p3/s3/j3-pending.log", "Log"),
    ]
    if root.local_items:
        urls.extend(
            [
                ("items/p1/s1/j1-finished.jl", "Items"),
                ("items/p2/s2/j2-running.jl", "Items"),
                ("items/p3/s3/j3-pending.jl", "Items"),
            ]
        )
    if exists:
        touch(chdir / "logs" / "p1" / "s1" / "j1-finished.log")
        touch(chdir / "logs" / "p2" / "s2" / "j2-running.log")
        exist = urls[0:2]
        no_exist = urls[2:3]

        if root.local_items:
            touch(chdir / "items" / "p1" / "s1" / "j1-finished.jl")
            touch(chdir / "items" / "p2" / "s2" / "j2-running.jl")
            exist += urls[3:5]
            no_exist += urls[5:6]
    else:
        exist = []
        no_exist = urls

    root.launcher.finished.add(get_finished_job("p1", "s1", "j1-finished"))
    root.launcher.processes[0] = ScrapyProcessProtocol("p2", "s2", "j2-running", env={}, args=[])
    root.poller.queues["quotesbot"].add("quotesbot", _job="j3-pending")

    if header:
        txrequest.requestHeaders = http_headers.Headers({b"X-Forwarded-Prefix": [b"/path/to"]})
    txrequest.method = "GET"
    content = root.children[b"jobs"].render(txrequest)
    text = content.decode()

    assert_headers(txrequest)
    assert_hrefs(exist, text, header)
    for url, _ in no_exist:
        assert url not in text

    if root.local_items:
        assert b"<th>Items</th>" in content
    else:
        assert b"<th>Items</th>" not in content

    if cancel:
        assert b"<th>Cancel</th>" in content
        if header:
            assert b' action="/path/to/cancel.json">' in content
        else:
            assert b' action="/cancel.json">' in content
        for job in ("j2-running", "j3-pending"):
            assert f' value="{job}">' in text
    else:
        assert b"<th>Cancel</th>" not in content
        assert b'/cancel.json">' not in content
    assert b' value="j1-finished">' not in content


@pytest.mark.parametrize("with_egg", [True, False])
@pytest.mark.parametrize("header", [True, False])
def test_home(txrequest, root, with_egg, header):
    if with_egg:
        root_add_version(root, "quotesbot", "0.1", "quotesbot")
        root.update_projects()

    if header:
        txrequest.requestHeaders = http_headers.Headers({b"X-Forwarded-Prefix": [b"/path/to"]})
    txrequest.method = "GET"
    content = root.children[b""].render(txrequest)
    text = content.decode()

    urls = [("jobs", "Jobs"), ("logs/", "Logs")]
    if root.local_items:
        urls.append(("items/", "Items"))

    assert_headers(txrequest)
    assert_hrefs(urls, text, header)

    if root.local_items:
        assert b'/items/">Items</a>' in content
    else:
        assert b'/items/">Items</a>' not in content

    projects = []
    if with_egg:
        projects.append("quotesbot")
    if has_settings():
        projects.append("localproject")

    if projects:
        assert b"<p>Scrapy projects:</p>" in content
        for project in projects:
            assert f"<li>{project}</li>" in text
    else:
        assert b"<p>No Scrapy projects yet.</p>" in content
        for project in projects:
            assert f"<li>{project}</li>" not in text


@pytest.mark.parametrize("basename", ["", "jobs"])
def test_validate(tmp_path, txrequest, root, basename, caplog):
    txrequest.method = "GET"
    content = root.children[basename.encode()].render(txrequest)
    path = tmp_path / "page.html"
    path.write_bytes(content)
    report = ValidatorInterface().validate([str(path)]).registry[str(path)]

    assert report is None, repr(report)
