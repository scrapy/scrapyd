# coding: utf-8
from tests.utils import OK, ERROR, BASE_URL, TRUE_AUTH, get_url, get, post


def test_listjobs():
    url = get_url('/listjobs.json')
    r = get(url, auth=TRUE_AUTH)
    resp_dict = r.json()
    assert resp_dict['status'] == OK
    for key in ['pending', 'running', 'finished']:
        assert key in resp_dict

def test_listprojects():
    url = get_url('/listprojects.json')
    r = get(url, auth=TRUE_AUTH)
    resp_dict = r.json()
    assert resp_dict['status'] == OK
    assert resp_dict['projects'] == []

def test_delproject():
    url = get_url('/delproject.json')
    data = {'project': 'not-exist'}
    r = post(url, data=data, auth=TRUE_AUTH)
    resp_dict = r.json()
    assert resp_dict['status'] == ERROR
