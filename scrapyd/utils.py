import sys
import os
from .sqlite import JsonSqliteDict
from subprocess import Popen, PIPE
from ConfigParser import NoSectionError
import json
from twisted.web import resource

from scrapyd.spiderqueue import SqliteSpiderQueue
from scrapy.utils.python import stringify_dict, unicode_to_str
from scrapyd.config import Config


class JsonResource(resource.Resource):

    json_encoder = json.JSONEncoder()

    def render(self, txrequest):
        r = resource.Resource.render(self, txrequest)
        return self.render_object(r, txrequest)

    def render_object(self, obj, txrequest):
        r = self.json_encoder.encode(obj) + "\n"
        txrequest.setHeader('Content-Type', 'application/json')
        txrequest.setHeader('Access-Control-Allow-Origin', '*')
        txrequest.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE')
        txrequest.setHeader('Access-Control-Allow-Headers',' X-Requested-With')
        txrequest.setHeader('Content-Length', len(r))
        return r

class UtilsCache:
    # array of project name that need to be invalided
    invalid_cached_projects = []

    def __init__(self):
        self.cache_manager = JsonSqliteDict(table="utils_cache_manager")

    # Invalid the spider's list's cache of a given project (by name)
    @staticmethod
    def invalid_cache(project):
        UtilsCache.invalid_cached_projects.append(project)

    def __getitem__(self, key):
        for p in UtilsCache.invalid_cached_projects:
            if p in self.cache_manager:
                del self.cache_manager[p]
        UtilsCache.invalid_cached_projects[:] = []
        return self.cache_manager[key]

    def __setitem__(self, key, value):
        self.cache_manager[key] = value

def get_spider_queues(config):
    """Return a dict of Spider Quees keyed by project name"""
    dbsdir = config.get('dbs_dir', 'dbs')
    if not os.path.exists(dbsdir):
        os.makedirs(dbsdir)
    d = {}
    for project in get_project_list(config):
        dbpath = os.path.join(dbsdir, '%s.db' % project)
        d[project] = SqliteSpiderQueue(dbpath)
    return d

def get_project_list(config):
    """Get list of projects by inspecting the eggs dir and the ones defined in
    the scrapyd.conf [settings] section
    """
    eggs_dir = config.get('eggs_dir', 'eggs')
    if os.path.exists(eggs_dir):
        projects = os.listdir(eggs_dir)
    else:
        projects = []
    try:
        projects += [x[0] for x in config.cp.items('settings')]
    except NoSectionError:
        pass
    return projects

def get_crawl_args(message):
    """Return the command-line arguments to use for the scrapy crawl process
    that will be started for this message
    """
    msg = message.copy()
    args = [unicode_to_str(msg['_spider'])]
    del msg['_project'], msg['_spider']
    settings = msg.pop('settings', {})
    for k, v in stringify_dict(msg, keys_only=False).items():
        args += ['-a']
        args += ['%s=%s' % (k, v)]
    for k, v in stringify_dict(settings, keys_only=False).items():
        args += ['-s']
        args += ['%s=%s' % (k, v)]
    return args

def get_spider_list(project, runner=None, pythonpath=None):
    """Return the spider list from the given project, using the given runner"""
    if "cache" not in get_spider_list.__dict__:
        get_spider_list.cache = UtilsCache()
    try:
        return get_spider_list.cache[project]
    except KeyError:
        pass
    if runner is None:
        runner = Config().get('runner')
    env = os.environ.copy()
    env['SCRAPY_PROJECT'] = project
    if pythonpath:
        env['PYTHONPATH'] = pythonpath
    pargs = [sys.executable, '-m', runner, 'list']
    proc = Popen(pargs, stdout=PIPE, stderr=PIPE, env=env)
    out, err = proc.communicate()
    if proc.returncode:
        msg = err or out or 'unknown error'
        raise RuntimeError(msg.splitlines()[-1])
    tmp = out.splitlines();
    get_spider_list.cache[project] = tmp
    return tmp
