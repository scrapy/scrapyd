import sys
import os

from scrapyd.orchestrator_client.api_interfaces.UserApi import UserApi
from scrapyd.orchestrator_client.api_interfaces.ProjectApi import ProjectApi
from scrapyd.orchestrator_client.api_interfaces.SpiderApi import SpiderApi
from scrapyd.orchestrator_client.api_interfaces.ScrapydInstanceApi import ScrapydInstanceApi
from scrapyd.orchestrator_client.exception.OrchestratorExceptionBase import OrchestratorExceptionBase

from scrapyd.sqlite import JsonSqliteDict
from subprocess import Popen, PIPE
import six
from six import iteritems
import socket
import json
import os
import sys
from subprocess import PIPE, Popen

import six
from scrapy.utils.misc import load_object
from six import iteritems
from twisted.web import resource
from twisted.python import log

from scrapyd.config import Config
from scrapy.utils.misc import load_object
import requests


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
        txrequest.setHeader('Access-Control-Allow-Headers', ' X-Requested-With')
        txrequest.setHeader('Content-Length', str(len(r)))
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
    """Return a dict of Spider Queues keyed by project name"""
    dbsdir = config.get('dbs_dir', 'dbs')
    if not os.path.exists(dbsdir):
        os.makedirs(dbsdir)
    d = {}
    for project in get_project_list(config):
        dbpath = os.path.join(dbsdir, '%s.db' % project)
        d[project] = SqliteSpiderQueue(dbpath)
    return d


def get_project_list(config):
    """Get list of projects by inspecting the eggs storage and the ones defined in
    the scrapyd.conf [settings] section
    """
    eggstorage = config.get('eggstorage', 'scrapyd.eggstorage.FilesystemEggStorage')
    eggstoragecls = load_object(eggstorage)
    eggstorage = eggstoragecls(config)
    projects = eggstorage.list_projects()
    projects.extend(x[0] for x in config.items('settings', default=[]))
    return projects


def get_latest_project_versions(config, project):
    eggstorage = config.get('eggstorage', 'scrapyd.eggstorage.FilesystemEggStorage')
    eggstoragecls = load_object(eggstorage)
    eggstorage = eggstoragecls(config)
    return max(eggstorage.list(project))


def native_stringify_dict(dct_or_tuples, encoding='utf-8', keys_only=True):
    """Return a (new) dict with unicode keys (and values when "keys_only" is
    False) of the given dict converted to strings. `dct_or_tuples` can be a
    dict or a list of tuples, like any dict constructor supports.
    """
    d = {}
    for k, v in iteritems(dict(dct_or_tuples)):
        k = _to_native_str(k, encoding)
        if not keys_only:
            if isinstance(v, dict):
                v = native_stringify_dict(v, encoding=encoding, keys_only=keys_only)
            elif isinstance(v, list):
                v = [_to_native_str(e, encoding) for e in v]
            else:
                v = _to_native_str(v, encoding)
        d[k] = v
    return d


def get_crawl_args(message):
    """Return the command-line arguments to use for the scrapy crawl process
    that will be started for this message
    """
    msg = message.copy()
    args = [_to_native_str(msg['_spider'])]
    del msg['_project'], msg['_spider']
    settings = msg.pop('settings', {})
    for k, v in native_stringify_dict(msg, keys_only=False).items():
        args += ['-a']
        args += ['%s=%s' % (k, v)]
    for k, v in native_stringify_dict(settings, keys_only=False).items():
        args += ['-s']
        args += ['%s=%s' % (k, v)]
    return args


def get_spider_list(project, runner=None, pythonpath=None, version=''):
    """Return the spider list from the given project, using the given runner"""
    if "cache" not in get_spider_list.__dict__:
        get_spider_list.cache = UtilsCache()
    try:
        return get_spider_list.cache[project][version]
    except KeyError:
        pass
    if runner is None:
        runner = Config().get('runner')
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'UTF-8'
    env['SCRAPY_PROJECT'] = project
    if pythonpath:
        env['PYTHONPATH'] = pythonpath
    if version:
        env['SCRAPY_EGG_VERSION'] = version
    pargs = [sys.executable, '-m', runner, 'list']
    proc = Popen(pargs, stdout=PIPE, stderr=PIPE, env=env)
    out, err = proc.communicate()
    if proc.returncode:
        msg = err or out or ''
        msg = msg.decode('utf8')
        raise RuntimeError(msg.encode('unicode_escape') if six.PY2 else msg)
    # FIXME: can we reliably decode as UTF-8?
    # scrapy list does `print(list)`
    tmp = out.decode('utf-8').splitlines()
    try:
        project_cache = get_spider_list.cache[project]
        project_cache[version] = tmp
    except KeyError:
        project_cache = {version: tmp}
    get_spider_list.cache[project] = project_cache
    return tmp


def _to_native_str(text, encoding='utf-8', errors='strict'):
    if isinstance(text, str):
        return text
    if not isinstance(text, (bytes, six.text_type)):
        raise TypeError('_to_native_str must receive a bytes, str or unicode '
                        'object, got %s' % type(text).__name__)
    if six.PY2:
        return text.encode(encoding, errors)
    else:
        return text.decode(encoding, errors)


def syncronize_orchestrator(config, scrapy_instance_id):
    project_list = get_project_list(config)

    project_api = ProjectApi()
    spider_api = SpiderApi()

    """
        Verifying that all the project on the instance are persisted in orchestrator's database
    """
    orchestrator_projects = project_api.get_all_by_instance_id(scrapy_instance_id)
    orchestrator_projects_name = [project_orch['name'] for project_orch in orchestrator_projects]
    if set(orchestrator_projects_name) != set(project_list):
        """
            This means we have differences between local data and orchestrator's data regarding projects
        """
        for project in orchestrator_projects:
            if project['name'] not in project_list:
                project_api.delete(project['id'])
            else:
                proj_version = get_latest_project_versions(config, project['name'])
                if project['version'] != proj_version:
                    project_api.update(project['name'], version=proj_version)
        for project in project_list:
            if project not in orchestrator_projects_name:
                project_api.add(project, get_latest_project_versions(config, project))

    """
        Updating spider from each project
    """
    for project in project_list:
        project_spiders = get_spider_list(project)
        available_spiders = spider_api.get_all_spiders_by_project_name(project)
        if set(available_spiders) != set(project_spiders):
            """
                This means we have differences between local data and orchestrator's data regarding spiders
            """
            for spider in available_spiders:
                if spider not in project_spiders:
                    spider_obj = spider_api.get_by_name(spider)
                    spider_api.delete(spider_obj['id'])
            for spider in project_spiders:
                if spider not in available_spiders:
                    project_obj = project_api.get_by_name(project)
                    spider_api.add(project_obj['id'], spider)


def register_scrapyd_instance(config, scrapyd_instance_api):
    """
                    If the scrapyd instance does not have an id assigned yet, it means this is the first run.
                    We proceed by registering a new user for this scrapyd instance, then we register the instance itself
                """
    authorization_api = UserApi.get_instance()
    authorization_api.register(config.get('orchestrator_user', None), config.get('orchestrator_password', None))
    scrapyd_instance = scrapyd_instance_api.add(get_ip(), config.get('http_port', None),
                                                config.get('orchestrator_user', None),
                                                config.get('orchestrator_password', None))
    log.msg(f"Registered scrapyd instance {str(scrapyd_instance)}")
    config.set('instance_id', str(scrapyd_instance['id']))
    return scrapyd_instance['id']

def establish_link_with_orchestrator(config):
    """
        Function for establishing the connection and data persistence with the orchestrator
    """
    scrapyd_instance_api = ScrapydInstanceApi()
    orchestrator_url = config.get('orchestrator_url', None)
    if orchestrator_url == '':
        return
    instance_id = config.get('instance_id', None)
    if instance_id == '':
        orchestrator_user = config.get('orchestrator_user', None)
        orchestrator_password = config.get('orchestrator_password', None)
        if orchestrator_user == '' or orchestrator_password == '':
            config.set('orchestrator_user', config.get('username', None))
            config.set('orchestrator_password', config.get('password', None))
        try:
            scrapy_instance_id = register_scrapyd_instance(config, scrapyd_instance_api)
            """
                Now we need to add existing projects & spiders to the orchestrator's database
            """
            log.msg(f"Scrapyd instance id {str(scrapy_instance_id)}")

            syncronize_orchestrator(config, scrapy_instance_id)

        except OrchestratorExceptionBase as e:
            log.msg(str(e))
    else:
        try:
            scrapyd_instance = scrapyd_instance_api.get(instance_id)
            if scrapyd_instance == {}:
                scrapy_instance_id = register_scrapyd_instance(config, scrapyd_instance_api)
            log.msg(f"Scrapyd instance id {str(scrapyd_instance['id'] if scrapyd_instance != {} else scrapy_instance_id)}")

            syncronize_orchestrator(config, scrapyd_instance['id'] if scrapyd_instance != {} else scrapy_instance_id)
        except OrchestratorExceptionBase as e:
            log.msg(str(e))


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        IP = requests.get('https://api.ipify.org').text
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP
