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

    content = root_with_egg.children[b"jobs"].render_GET(txrequest)

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())
    content_length = headers.pop(b"Content-Length")

    assert len(content_length) == 1
    assert isinstance(content_length[0], bytes)
    assert int(content_length[0])
    assert headers == {b"Content-Type": [b"text/html; charset=utf-8"]}
    assert content.decode().startswith(
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="utf-8">\n    <meta name="viewport" content='
    )
    if root_with_egg.local_items:
        assert b"Items</th>" in content
    else:
        assert b"Items</th>" not in content


def test_render_home(txrequest, root_with_egg):
    content = root_with_egg.children[b""].render_GET(txrequest)

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())
    content_length = headers.pop(b"Content-Length")

    assert len(content_length) == 1
    assert isinstance(content_length[0], bytes)
    assert int(content_length[0])
    assert headers == {b"Content-Type": [b"text/html; charset=utf-8"]}
    assert b"<p>Scrapy projects:</p>" in content
    assert b"<li>quotesbot</li>" in content
    if root_with_egg.local_items:
        assert b"Items</a>" in content
    else:
        assert b"Items</a>" not in content
    if has_settings():
        assert b"localproject" in content
    else:
        assert b"localproject" not in content
