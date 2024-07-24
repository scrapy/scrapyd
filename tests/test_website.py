import os

from twisted.web import resource
from twisted.web.test._util import _render
from twisted.web.test.requesthelper import DummyRequest

from scrapyd.jobstorage import Job
from scrapyd.launcher import ScrapyProcessProtocol
from tests import has_settings


# Derived from test_emptyChildUnicodeParent.
# https://github.com/twisted/twisted/blob/trunk/src/twisted/web/test/test_static.py
def test_render_logs_dir(txrequest, root):
    os.makedirs(os.path.join("logs", "quotesbot"))

    file = root.children[b"logs"]
    request = DummyRequest([b""])
    child = resource.getChildForRequest(file, request)

    content = child.render(request)

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

    content = root_with_egg.children[b"jobs"].render(txrequest)
    expect_headers = {
        b"Content-Type": [b"text/html; charset=utf-8"],
        b"Content-Length": [b"1744"],
    }
    if root_with_egg.local_items:
        expect_headers[b"Content-Length"] = [b"1702"]

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())

    assert headers == expect_headers
    assert content.decode().startswith(
        '<html><head><title>Scrapyd</title><style type="text/css">#jobs>thead td {text-align: center; font-weight'
    )
    if root_with_egg.local_items:
        assert b"display: none" not in content
    else:
        assert b"display: none" in content


def test_render_home(txrequest, root_with_egg):
    content = root_with_egg.children[b""].render_GET(txrequest)
    expect_headers = {
        b"Content-Type": [b"text/html; charset=utf-8"],
        b"Content-Length": [b"736" if has_settings() else b"714"],
    }
    if root_with_egg.local_items:
        expect_headers[b"Content-Length"] = [b"751"]

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())

    assert headers == expect_headers
    assert b"Available projects" in content
    if root_with_egg.local_items:
        assert b"Items" in content
    else:
        assert b"Items" not in content
