# coding: utf-8
from tests.utils import BASE_URL, TRUE_AUTH, get_url, get


def test_homepage():
    r = get(BASE_URL, auth=TRUE_AUTH)

def test_pages_with_auth_pass():
    for page in ['/jobs']:  # '/logs'
        r = get(get_url(page), auth=TRUE_AUTH)
