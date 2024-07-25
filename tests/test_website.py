import os

import pytest
from twisted.web import http_headers, resource
from twisted.web.test._util import _render
from twisted.web.test.requesthelper import DummyRequest

from scrapyd.jobstorage import Job
from scrapyd.launcher import ScrapyProcessProtocol
from tests import has_settings, root_add_version


# Derived from test_emptyChildUnicodeParent.
# https://github.com/twisted/twisted/blob/trunk/src/twisted/web/test/test_static.py
def test_render_logs_dir(txrequest, root):
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
def test_render_logs_file(txrequest, root):
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


def test_render_jobs(txrequest, root_with_egg):
    root_with_egg.launcher.finished.add(Job("p1", "s1", "j1"))
    root_with_egg.launcher.processes[0] = ScrapyProcessProtocol("p2", "s2", "j2", {}, [])
    root_with_egg.poller.queues["quotesbot"].add("quotesbot", _job="j3")

    content = root_with_egg.children[b"jobs"].render_GET(txrequest)

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())
    content_length = headers.pop(b"Content-Length")

    assert len(content_length) == 1
    assert isinstance(content_length[0], bytes)
    assert int(content_length[0])
    assert headers == {b"Content-Type": [b"text/html; charset=utf-8"]}
    if root_with_egg.local_items:
        assert b"Items</th>" in content
    else:
        assert b"Items</th>" not in content


@pytest.mark.parametrize("with_egg", [True, False])
@pytest.mark.parametrize("header", [True, False])
def test_render_home(txrequest, root, with_egg, header):
    if with_egg:
        root_add_version(root, "quotesbot", "0.1", "quotesbot")
        root.update_projects()

    if header:
        txrequest.requestHeaders = http_headers.Headers({b"X-Forwarded-Prefix": [b"/path/to"]})
    content = root.children[b""].render_GET(txrequest)
    text = content.decode()

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())
    content_length = headers.pop(b"Content-Length")

    assert len(content_length) == 1
    assert isinstance(content_length[0], bytes)
    assert int(content_length[0])
    assert headers == {b"Content-Type": [b"text/html; charset=utf-8"]}

    urls = [("jobs", "Jobs"), ("logs/", "Logs")]
    if root.local_items:
        urls.append(("items/", "Items"))

    for href, name in urls:
        if header:
            assert f'<a href="/path/to/{href}">{name}</a>' in text
        else:
            assert f'<a href="/{href}">{name}</a>' in text

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
