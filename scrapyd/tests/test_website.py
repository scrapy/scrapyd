import pytest
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.website import Root


@pytest.fixture
def txrequest():
    tcp_channel = DummyChannel.TCP()
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(tcp_channel)
    return Request(http_channel)


@pytest.fixture
def scrapyd_site():
    config = Config()
    app = application(config)
    return Root(config, app)


class TestWebsite:
    def test_render_jobs(self, txrequest, scrapyd_site):
        content = scrapyd_site.children[b'jobs'].render_GET(txrequest)
        expect_headers = {
            b'Content-Type': [b'text/html; charset=utf-8'],
            b'Content-Length': [b'1548']
        }
        headers = txrequest.responseHeaders.getAllRawHeaders()
        assert dict(headers) == expect_headers
        initial = '''<html>

<head>
    <title>Scrapyd</title>'''
        assert content.decode().startswith(initial)

    def test_render_home(self, txrequest, scrapyd_site):
        content = scrapyd_site.children[b''].render_GET(txrequest)
        assert b'Available projects' in content
        headers = dict(txrequest.responseHeaders.getAllRawHeaders())
        assert headers[b'Content-Type'] == [b'text/html; charset=utf-8']
        # content-length different between my localhost and build environment
        assert b'Content-Length' in headers
