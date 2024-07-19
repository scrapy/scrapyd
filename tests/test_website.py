def test_render_jobs(txrequest, site_with_egg):
    content = site_with_egg.children[b"jobs"].render(txrequest)
    expect_headers = {
        b"Content-Type": [b"text/html; charset=utf-8"],
        b"Content-Length": [b"643"],
    }
    if site_with_egg.local_items:
        expect_headers[b"Content-Length"] = [b"601"]

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())

    assert headers == expect_headers
    assert content.decode().startswith(
        '<html><head><title>Scrapyd</title><style type="text/css">#jobs>thead td {text-align: center; font-weight'
    )
    if site_with_egg.local_items:
        assert b"display: none" not in content
    else:
        assert b"display: none" in content


def test_render_home(txrequest, site_with_egg):
    content = site_with_egg.children[b""].render_GET(txrequest)
    expect_headers = {
        b"Content-Type": [b"text/html; charset=utf-8"],
        b"Content-Length": [b"714"],
    }
    if site_with_egg.local_items:
        expect_headers[b"Content-Length"] = [b"751"]

    headers = dict(txrequest.responseHeaders.getAllRawHeaders())

    assert headers == expect_headers
    assert b"Available projects" in content
    if site_with_egg.local_items:
        assert b"Items" in content
    else:
        assert b"Items" not in content
