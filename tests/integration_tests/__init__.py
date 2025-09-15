from urllib.parse import urljoin

import requests


def req(method, path, auth=None, status=200, server_info=None, **kwargs):
    """Make HTTP request to scrapyd server."""
    if server_info is None:
        # Default behavior - simple request to existing server
        url = urljoin("http://127.0.0.1:6800", path)
        response = getattr(requests, method)(url, auth=auth, **kwargs)
        assert response.status_code == status, f"{status} != {response.status_code}"
        return response
    else:
        # Using server_info - make request to specific server
        url = urljoin(f"http://127.0.0.1:{server_info['port']}", path)
        auth = server_info["auth"]
        response = getattr(requests, method)(url, auth=auth, **kwargs)
        assert response.status_code == status, f"{status} != {response.status_code}"
        return response


def req_with_auth_check(method, path, server_info, status=200, **kwargs):
    """Make request with authentication checks (for authenticated servers)."""
    url = urljoin(f"http://127.0.0.1:{server_info['port']}", path)

    # Test without auth and with bad auth - should get 401
    for badauth in (None, ("baduser", "badpass")):
        response = getattr(requests, method)(url, auth=badauth, **kwargs)
        assert response.status_code == 401, f"Expected 401 but got {response.status_code}"
        assert response.text == "Unauthorized"

    # Test with correct auth
    response = getattr(requests, method)(url, auth=server_info["auth"], **kwargs)
    assert response.status_code == status, f"{status} != {response.status_code}"
    return response
