# coding: utf-8
def test_fixture(fixture):
    requests = fixture()
    assert requests
