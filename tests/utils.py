# coding: utf-8
try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

import requests


OK = 'ok'
ERROR = 'error'
BASE_URL = 'http://127.0.0.1:6800'
TRUE_AUTH = ('hello12345', '67890world')
FAKE_AUTH = ('username', 'password')


def get_url(url, base=BASE_URL):
    return_url = urljoin(base, url)
    return return_url

def _get(url, auth=None):
    print(">>> GET %s with auth %s" % (url, auth))
    r = requests.get(url, auth=auth)
    print("<<< %s" % r.status_code)
    return r

def _post(url, data, auth=None):
    print(">>> POST %s to %s with auth %s" % (data, url, auth))
    r = requests.post(url, data=data, auth=auth)
    print("<<< %s" % r.status_code)
    return r

def _check_response(r):
    if r.status_code == 401:
        assert r.text == 'Unauthorized'
    else:
        assert r.status_code == 200
    try:
        print(r.json())
    except ValueError as err:
        print(r.text)

def _test_auth_fail(method, url, data=None):
    for auth in [None, FAKE_AUTH]:
        if method == 'get':
            r = _get(url, auth=auth)
        else:
            r = _post(url, data=data, auth=auth)

def get(url, auth=None):
    _test_auth_fail('get', url)
    r = _get(url, auth=auth)
    _check_response(r)
    return r

def post(url, data, auth=None):
    _test_auth_fail('post', url, data=data)
    r = _post(url, data=data, auth=auth)
    _check_response(r)
    return r
