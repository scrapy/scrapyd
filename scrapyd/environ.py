import os
from six.moves.urllib.parse import urlparse, urlunparse

from w3lib.url import path_to_file_uri
from zope.interface import implementer

from .interfaces import IEnvironment

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

    def get_environment(self, message, slot):
        project = message['_project']
        env = self.initenv.copy()
        env['SCRAPY_SLOT'] = str(slot)
        env['SCRAPY_PROJECT'] = project
        env['SCRAPY_SPIDER'] = message['_spider']
        env['SCRAPY_JOB'] = message['_job']
        if '_version' in message:
            env['SCRAPY_EGG_VERSION'] = message['_version']
        if project in self.settings:
            env['SCRAPY_SETTINGS_MODULE'] = self.settings[project]
        if self.logs_dir:
            env['SCRAPY_LOG_FILE'] = self._get_file(message, self.logs_dir, 'log')
        if self.items_dir:
            env['SCRAPY_FEED_URI'] = self._get_feed_uri(message, 'jl')
        return env

    def _get_feed_uri(self, message, ext):
        url = urlparse(self.items_dir)
        if url.scheme.lower() in ['', 'file']:
            return path_to_file_uri(self._get_file(message, url.path, ext))
        return urlunparse((url.scheme,
                           url.netloc,
                           '/'.join([url.path,
                                     message['_project'],
                                     message['_spider'],
                                     '%s.%s' % (message['_job'], ext)]),
                           url.params,
                           url.query,
                           url.fragment))

    def _get_file(self, message, dir, ext):
        logsdir = os.path.join(dir, message['_project'], \
            message['_spider'])
        if not os.path.exists(logsdir):
            os.makedirs(logsdir)
        to_delete = sorted((os.path.join(logsdir, x) for x in \
            os.listdir(logsdir)), key=os.path.getmtime)[:-self.jobs_to_keep]
        for x in to_delete:
            os.remove(x)
        return os.path.join(logsdir, "%s.%s" % (message['_job'], ext))
