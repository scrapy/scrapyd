
def test_fixture(fixture):
    requests = fixture()
    assert requests
