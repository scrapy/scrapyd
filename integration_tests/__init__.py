from urllib.parse import urljoin

import requests


def req(method, path, auth=None, status=200, **kwargs):
    url = urljoin("http://127.0.0.1:6800", path)

    for badauth in (None, ("baduser", "badpass")):
        response = getattr(requests, method)(url, auth=badauth, **kwargs)

        assert response.status_code == 401, f"401 != {response.status_code}"
        assert response.text == "Unauthorized"

    response = getattr(requests, method)(url, auth=("hello12345", "67890world"), **kwargs)

    assert response.status_code == status, f"{status} != {response.status_code}"

    return response
