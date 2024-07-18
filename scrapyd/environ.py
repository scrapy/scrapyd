import json
import os
from urllib.parse import urlparse, urlunparse

from w3lib.url import path_to_file_uri
from zope.interface import implementer

from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEnvironment


@implementer(IEnvironment)
class Environment(object):

    def __init__(self, config, initenv=os.environ):
        self.dbs_dir = config.get('dbs_dir', 'dbs')
        self.logs_dir = config.get('logs_dir', 'logs')
        self.items_dir = config.get('items_dir', '')
        self.jobs_to_keep = config.getint('jobs_to_keep', 5)
        if config.cp.has_section('settings'):
            self.settings = dict(config.cp.items('settings'))
        else:
            self.settings = {}
        self.initenv = initenv

    def get_settings(self, message):
        settings = {}
        if self.logs_dir:
            settings['LOG_FILE'] = self._get_file(message, self.logs_dir, 'log')
        if self.items_dir:
            settings['FEEDS'] = json.dumps({self._get_feed_uri(message, 'jl'): {'format': 'jsonlines'}})
        return settings

    def get_environment(self, message, slot):
        project = message['_project']
        env = self.initenv.copy()
        env['SCRAPY_PROJECT'] = project
        env['SCRAPYD_SLOT'] = str(slot)
        env['SCRAPYD_SPIDER'] = message['_spider']
        env['SCRAPYD_JOB'] = message['_job']
        if '_version' in message:
            env['SCRAPYD_EGG_VERSION'] = message['_version']
        if project in self.settings:
            env['SCRAPY_SETTINGS_MODULE'] = self.settings[project]
        if self.logs_dir:
            env['SCRAPYD_LOG_FILE'] = self._get_file(message, self.logs_dir, 'log')
        if self.items_dir:
            env['SCRAPYD_FEED_URI'] = self._get_feed_uri(message, 'jl')
        return env

    def _get_feed_uri(self, message, extension):
        url = urlparse(self.items_dir)
        if url.scheme.lower() in ['', 'file']:
            return path_to_file_uri(self._get_file(message, url.path, extension))
        return urlunparse((url.scheme,
                           url.netloc,
                           '/'.join([url.path,
                                     message['_project'],
                                     message['_spider'],
                                     f"{message['_job']}.{extension}"]),
                           url.params,
                           url.query,
                           url.fragment))

    def _get_file(self, message, directory, extension):
        resolvedir = os.path.realpath(directory)
        projectdir = os.path.realpath(os.path.join(resolvedir, message['_project']))
        spiderdir = os.path.realpath(os.path.join(projectdir, message['_spider']))
        filepath = os.path.realpath(os.path.join(spiderdir, f"{message['_job']}.{extension}"))

        if (
            os.path.commonprefix((projectdir, resolvedir)) != resolvedir
            or os.path.commonprefix((spiderdir, projectdir)) != projectdir
            or os.path.commonprefix((filepath, spiderdir)) != spiderdir
        ):
            raise DirectoryTraversalError(f"{filepath} is not under the {directory} ({resolvedir}) directory")

        if not os.path.exists(spiderdir):
            os.makedirs(spiderdir)

        to_delete = sorted(
            (os.path.join(spiderdir, name) for name in os.listdir(spiderdir)),
            key=os.path.getmtime,
        )[:-self.jobs_to_keep]

        for path in to_delete:
            try:
                os.remove(path)
            except OSError:
                pass

        return filepath
