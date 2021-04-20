import pytest
import requests


@pytest.fixture
def fixture():
    def get_requests_lib(**kwargs):
        return requests
    yield get_requests_lib
