import pytest
pytestmark = [pytest.mark.integration, pytest.mark.auth]
from tests.integration_tests import req_with_auth_check


def test_auth_daemonstatus(auth_server):
    """Test daemon status with authentication."""
    response = req_with_auth_check("get", "/daemonstatus.json", auth_server)
    data = response.json()
    data.pop("node_name")
    assert data == {"status": "ok", "running": 0, "pending": 0, "finished": 0}


def test_auth_listprojects(auth_server):
    """Test list projects with authentication."""
    response = req_with_auth_check("get", "/listprojects.json", auth_server)
    data = response.json()
    data.pop("node_name")
    assert data == {"status": "ok", "projects": []}


def test_auth_listjobs(auth_server):
    """Test list jobs with authentication."""
    response = req_with_auth_check("get", "/listjobs.json", auth_server)
    data = response.json()
    data.pop("node_name")
    assert data == {"status": "ok", "pending": [], "running": [], "finished": []}