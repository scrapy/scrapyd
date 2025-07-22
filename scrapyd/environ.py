import json
import os
from contextlib import suppress
from posixpath import join as urljoin
from urllib.parse import urlsplit

from w3lib.url import path_to_file_uri
from zope.interface import implementer

from scrapyd.interfaces import IEnvironment
from scrapyd.utils import get_file_path, local_items


@implementer(IEnvironment)
class Environment:
    def __init__(self, config, initenv=os.environ):
        self.dbs_dir = config.get("dbs_dir", "dbs")
        self.logs_dir = config.get("logs_dir", "logs")
        self.items_dir = config.get("items_dir", "")
        self.jobs_dir = config.get("jobs_dir", "")
        self.jobs_to_keep = config.getint("jobs_to_keep", 5)
        self.settings = dict(config.items("settings", default=[]))
        self.initenv = initenv

    def get_settings(self, message):
        settings = {}
        if self.logs_dir:
            settings["LOG_FILE"] = self._prepare_file(message, self.logs_dir, "log")
        if self.items_dir:
            settings["FEEDS"] = json.dumps({self._get_feeds(message, "jl"): {"format": "jsonlines"}})
        if self.jobs_dir:
            settings["JOBDIR"] = get_file_path(
                self.jobs_dir, message["_project"], message["_spider"], message["_job"]
            ).path
        return settings

    def get_environment(self, message, slot):
        project = message["_project"]

        env = self.initenv.copy()
        env["SCRAPY_PROJECT"] = project
        # If the version is not provided, then the runner uses the default version, determined by egg storage.
        if "_version" in message:
            env["SCRAPYD_EGG_VERSION"] = message["_version"]
        # Scrapy discovers the same scrapy.cfg files as Scrapyd. So, this is only needed if users are adding [settings]
        # sections to Scrapyd configuration files (which Scrapy doesn't discover). This might lead to strange behavior
        # if an egg project and a [settings] project have the same name (unlikely). Preserved, since committed in 2010.
        if project in self.settings:
            env["SCRAPY_SETTINGS_MODULE"] = self.settings[project]

        return env

    def _get_feeds(self, message, extension):
        parsed = urlsplit(self.items_dir)

        if local_items(self.items_dir, parsed):
            # File URLs do not have query or fragment components. https://www.rfc-editor.org/rfc/rfc8089#section-2
            return path_to_file_uri(self._prepare_file(message, parsed.path, extension))

        path = urljoin(parsed.path, message["_project"], message["_spider"], f"{message['_job']}.{extension}")
        return parsed._replace(path=path).geturl()

    def _prepare_file(self, message, directory, extension):
        file_path = get_file_path(directory, message["_project"], message["_spider"], f'{message["_job"]}.{extension}')

        parent = file_path.dirname()  # returns a str
        if not os.path.exists(parent):
            os.makedirs(parent)

        to_delete = sorted(
            (os.path.join(parent, name) for name in os.listdir(parent)),
            key=os.path.getmtime,
        )[: -self.jobs_to_keep]
        for path in to_delete:
            with suppress(OSError):
                os.remove(path)

        return file_path.path
