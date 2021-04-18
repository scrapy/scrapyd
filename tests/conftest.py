# coding: utf-8
import pytest
import requests

import scrapyd


@pytest.fixture
def fixture():
    def get_requests_lib(**kwargs):
        return requests
    yield get_requests_lib
