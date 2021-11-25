class TestWebsite:
    def test_render_jobs(self, txrequest, site_no_egg):
        content = site_no_egg.children[b'jobs'].render(txrequest)
        expect_headers = {
            b'Content-Type': [b'text/html; charset=utf-8'],
            b'Content-Length': [b'643']
        }
        headers = txrequest.responseHeaders.getAllRawHeaders()
        assert dict(headers) == expect_headers
        initial = '<html><head><title>Scrapyd</title><style type="text/css">#jobs>thead td {text-align: center; font-weight'
        assert content.decode().startswith(initial)

    def test_render_home(self, txrequest, site_no_egg):
        content = site_no_egg.children[b''].render_GET(txrequest)
        assert b'Available projects' in content
        headers = dict(txrequest.responseHeaders.getAllRawHeaders())
        assert headers[b'Content-Type'] == [b'text/html; charset=utf-8']
        # content-length different between my localhost and build environment
        assert b'Content-Length' in headers
