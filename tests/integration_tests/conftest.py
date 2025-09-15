import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests
from requests.exceptions import ConnectionError


@pytest.fixture(scope="session", autouse=True)
def scrapyd_server(tmp_path_factory):
    """
    Start a scrapyd server for the integration test session.
    First checks if one is already running, otherwise starts a fresh one.
    """
    try:
        # Check if a server is already running on port 6800
        response = requests.get("http://127.0.0.1:6800/daemonstatus.json", timeout=1)
        if response.status_code == 200:
            # Server is running without auth
            yield {"port": 6800, "auth": None}
            return
    except (ConnectionError, requests.exceptions.Timeout):
        pass

    # Start a fresh server without authentication for general integration tests
    temp_dir = tmp_path_factory.mktemp("scrapyd_integration")

    # Create required directories
    (temp_dir / "eggs").mkdir(exist_ok=True)
    (temp_dir / "logs").mkdir(exist_ok=True)
    (temp_dir / "dbs").mkdir(exist_ok=True)

    config_file = temp_dir / "scrapyd.conf"
    config_content = f"""[scrapyd]
eggs_dir = {temp_dir / "eggs"}
logs_dir = {temp_dir / "logs"}
dbs_dir = {temp_dir / "dbs"}
http_port = 6800
debug = on
"""
    config_file.write_text(config_content)

    env = os.environ.copy()
    env["SCRAPYD_CONFIG"] = str(config_file)

    process = subprocess.Popen([sys.executable, "-m", "scrapyd"], env=env)

    # Wait for the server to start
    for i in range(30):
        try:
            response = requests.get("http://127.0.0.1:6800/daemonstatus.json", timeout=1)
            if response.status_code == 200:
                break
        except (ConnectionError, requests.exceptions.Timeout):
            time.sleep(0.5)

        if process.poll() is not None:
            pytest.fail(f"Scrapyd server process died with return code {process.returncode}")
    else:
        process.terminate()
        process.wait()
        pytest.fail("Scrapyd server failed to start after 30 attempts")

    yield {"port": 6800, "auth": None}

    process.terminate()
    process.wait()


@pytest.fixture(scope="function")
def auth_server(tmp_path):
    """Start a scrapyd server with authentication for auth-specific tests."""
    # Create required directories
    (tmp_path / "eggs").mkdir(exist_ok=True)
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "dbs").mkdir(exist_ok=True)

    config_file = tmp_path / "scrapyd.conf"
    config_content = f"""[scrapyd]
eggs_dir = {tmp_path / "eggs"}
logs_dir = {tmp_path / "logs"}
dbs_dir = {tmp_path / "dbs"}
http_port = 6803
username = hello12345
password = 67890world
debug = on
"""
    config_file.write_text(config_content)

    env = os.environ.copy()
    env["SCRAPYD_CONFIG"] = str(config_file)

    process = subprocess.Popen([sys.executable, "-m", "scrapyd"], env=env)

    # Wait for the server to start
    for i in range(30):
        try:
            response = requests.get("http://127.0.0.1:6803/daemonstatus.json", timeout=1)
            # Should get 401 without auth, meaning server is up with auth enabled
            if response.status_code == 401:
                break
        except (ConnectionError, requests.exceptions.Timeout):
            time.sleep(0.5)

        if process.poll() is not None:
            pytest.fail(f"Auth server process died with return code {process.returncode}")
    else:
        process.terminate()
        process.wait()
        pytest.fail("Auth server failed to start after 30 attempts")

    yield {"port": 6803, "auth": ("hello12345", "67890world")}

    process.terminate()
    process.wait()
