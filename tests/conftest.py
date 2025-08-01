import logging
import os
import shutil
import warnings
from pathlib import Path

import pytest
from setuptools import setup
from setuptools.warnings import SetuptoolsDeprecationWarning
from twisted.web import http
from twisted.web.http import Request
from twisted.web.test.requesthelper import DummyChannel

from scrapyd import Config
from scrapyd.app import application
from scrapyd.interfaces import IEnvironment
from scrapyd.webservice import spider_list
from scrapyd.website import Root
from tests import root_add_version

BASEDIR = Path(__file__).parent.resolve()


def pytest_configure(config):
    cwd = Path.cwd()
    projects_dir = BASEDIR / "projects"

    # Hide bdist_egg's INFO messages. setup() calls setuptools.logging.configure(), which calls logging.basicConfig(),
    # which "does nothing if the root logger already has handlers configured."
    # https://docs.python.org/3/library/logging.html#logging.basicConfig
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)
    logging.basicConfig(handlers=[handler])

    os.chdir(projects_dir)
    try:
        for project_path in projects_dir.iterdir():
            project = project_path.name
            if project in {"dist", "project.egg-info"}:
                continue

            entrypoint_missing = project == "entrypoint_missing"

            # Avoid "UserWarning: Module mybot was already imported" in tests.
            package = "mybot"

            packages = [package]
            if (projects_dir / project / "spiders").exists():
                packages.append(f"{package}.spiders")

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=SetuptoolsDeprecationWarning)

                setup(
                    script_args=["bdist_egg"],
                    name="project",
                    packages=packages,
                    package_dir={package: project},
                    entry_points={"scrapy": [] if entrypoint_missing else [f"settings = {package}.settings"]},
                    # `zip_safe` avoids "zip_safe flag not set; analyzing archive contents...".
                    zip_safe=True,
                )

            dist_dir = projects_dir / "dist"
            # Names are like "project-0.0.0-py3.12.egg".
            egg_file = next(path for path in dist_dir.iterdir() if path.suffix == ".egg")
            egg_file.rename(BASEDIR / "fixtures" / f"{project}.egg")

            # `--build-scripts` avoids "'build/scripts-3.##' does not exist -- can't clean it".
            setup(script_args=["clean", "--all", "--build-scripts=build"], packages=packages)
    finally:
        os.chdir(cwd)


@pytest.fixture(autouse=True)
def _clear_spider_list_cache():
    spider_list.cache.clear()


@pytest.fixture
def txrequest():
    http_channel = http.HTTPChannel()
    http_channel.makeConnection(DummyChannel.TCP())
    return Request(http_channel)


# Use this fixture when testing the Scrapyd web UI or API or writing configuration files.
@pytest.fixture
def chdir(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture(
    params=[
        None,
        (("items_dir", "items"), ("jobstorage", "scrapyd.jobstorage.SqliteJobStorage")),
    ],
    ids=["default", "custom"],
)
def config(request, chdir):
    if request.param:
        shutil.copytree(BASEDIR / "fixtures" / "filesystem", chdir, dirs_exist_ok=True)
    config = Config()
    if request.param:
        for key, value in request.param:
            config.cp.set(Config.SECTION, key, value)
    return config


@pytest.fixture
def app(config):
    return application(config)


@pytest.fixture
def environ(app):
    return app.getComponent(IEnvironment)


@pytest.fixture
def root(config, app):
    return Root(config, app)


@pytest.fixture
def root_with_egg(root):
    root_add_version(root, "mybot", "0.1", "mybot")
    root.update_projects()
    return root
