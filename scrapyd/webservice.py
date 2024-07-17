import functools
import re
import sys
import traceback
import uuid
import zipfile
from copy import copy
from io import BytesIO

from twisted.python import log
from twisted.web import error, http

from scrapyd.exceptions import MissingRequiredArgument
from scrapyd.jobstorage import job_items_url, job_log_url
from scrapyd.utils import JsonResource, UtilsCache, get_spider_list, native_stringify_dict

# Allow the same characters as Setuptools. Setuptools uses underscores for replacement in filenames, and hyphens
# for replacement in distributions. Quotes and spaces are allowed in case a config sets `project = "my project"`.
# https://github.com/pypa/setuptools/blob/e304e4d/setuptools/_distutils/command/install_egg_info.py#L74
DISALLOWED_CHARACTERS = re.compile(b"""[^A-Za-z0-9."'\\s_-]""")


def with_project(required=True):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(resource, txrequest):
            project = txrequest.args.pop(b'project', [b''])[0]
            if required and not project:
                raise error.Error(code=http.BAD_REQUEST, message=b"'project' parameter is required")
            if DISALLOWED_CHARACTERS.search(project):
                raise error.Error(code=http.BAD_REQUEST, message=b"project '%b' is invalid" % project)
            return func(resource, txrequest, project.decode())

        return wrapper

    return decorator


def _get_required_param(args, param):
    try:
        return args[param]
    except KeyError as e:
        raise MissingRequiredArgument(str(e))


def _pop_required_param(args, param):
    try:
        return args.pop(param)
    except KeyError as e:
        raise MissingRequiredArgument(str(e))


class WsResource(JsonResource):
    def __init__(self, root):
        JsonResource.__init__(self)
        self.root = root

    def render(self, txrequest: http.Request):
        try:
            return JsonResource.render(self, txrequest).encode('utf-8')
        except Exception as e:
            if isinstance(e, error.Error):
                txrequest.setResponseCode(e.args[0])
            if self.root.debug:
                return traceback.format_exc().encode('utf-8')
            log.err()
            if isinstance(e, MissingRequiredArgument):
                message = f"{e} parameter is required"
            else:
                message = f"{type(e).__name__}: {str(e)}"
            r = self._error(message)
            return self.encode_object(r, txrequest).encode('utf-8')

    def render_OPTIONS(self, txrequest):
        methods = ['OPTIONS', 'HEAD']
        if hasattr(self, 'render_GET'):
            methods.append('GET')
        if hasattr(self, 'render_POST'):
            methods.append('POST')
        txrequest.setHeader('Allow', ', '.join(methods))
        txrequest.setResponseCode(http.NO_CONTENT)

    def _error(self, message):
        return {"node_name": self.root.nodename, "status": "error", "message": message}


class DaemonStatus(WsResource):
    def render_GET(self, txrequest):
        pending = sum(q.count() for q in self.root.poller.queues.values())
        running = len(self.root.launcher.processes)
        finished = len(self.root.launcher.finished)

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished,
        }


class Schedule(WsResource):
    @with_project()
    def render_POST(self, txrequest, project):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        settings = args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = {k: v[0] for k, v in args.items()}
        spider = _pop_required_param(args, 'spider')
        version = args.get('_version', '')
        priority = float(args.pop('priority', 0))
        spiders = get_spider_list(project, version=version)
        if spider not in spiders:
            return self._error("spider '%s' not found" % spider)
        args['settings'] = settings
        jobid = args.pop('jobid', uuid.uuid1().hex)
        args['_job'] = jobid
        self.root.scheduler.schedule(project, spider, priority=priority, **args)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}


class Cancel(WsResource):
    @with_project()
    def render_POST(self, txrequest, project):
        args = {k: v[0] for k, v in native_stringify_dict(copy(txrequest.args), keys_only=False).items()}
        jobid = _get_required_param(args, 'job')
        # Instead of os.name, use sys.platform, which disambiguates Cygwin, which implements SIGINT not SIGBREAK.
        # https://cygwin.com/cygwin-ug-net/kill.html
        # https://github.com/scrapy/scrapy/blob/06f9c289d1c92dbb8e41a837b886e5cadb81a061/tests/test_crawler.py#L886
        signal = args.get('signal', 'INT' if sys.platform != 'win32' else 'BREAK')
        prevstate = None
        try:
            queue = self.root.poller.queues[project]
        except KeyError as e:
            return self._error(f"project {e} not found")
        c = queue.remove(lambda x: x["_job"] == jobid)
        if c:
            prevstate = "pending"
        spiders = self.root.launcher.processes.values()
        for s in spiders:
            if s.project == project and s.job == jobid:
                s.transport.signalProcess(signal)
                prevstate = "running"
        return {"node_name": self.root.nodename, "status": "ok", "prevstate": prevstate}


class AddVersion(WsResource):
    @with_project()
    def render_POST(self, txrequest, project):
        egg = _pop_required_param(txrequest.args, b'egg')[0]
        if not zipfile.is_zipfile(BytesIO(egg)):
            return self._error("egg is not a ZIP file (if using curl, use egg=@path not egg=path)")
        eggf = BytesIO(egg)
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        version = _get_required_param(args, 'version')[0]
        self.root.eggstorage.put(eggf, project, version)
        spiders = get_spider_list(project, version=version)
        self.root.update_projects()
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok", "project": project, "version": version,
                "spiders": len(spiders)}


class ListProjects(WsResource):
    def render_GET(self, txrequest):
        projects = list(self.root.scheduler.list_projects())
        return {"node_name": self.root.nodename, "status": "ok", "projects": projects}


class ListVersions(WsResource):
    @with_project()
    def render_GET(self, txrequest, project):
        versions = self.root.eggstorage.list(project)
        return {"node_name": self.root.nodename, "status": "ok", "versions": versions}


class ListSpiders(WsResource):
    @with_project()
    def render_GET(self, txrequest, project):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        version = args.get('_version', [''])[0]
        spiders = get_spider_list(project, runner=self.root.runner, version=version)
        return {"node_name": self.root.nodename, "status": "ok", "spiders": spiders}


class Status(WsResource):
    @with_project(required=False)
    def render_GET(self, txrequest, project):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        job = _get_required_param(args, 'job')[0]

        spiders = self.root.launcher.processes.values()
        queues = self.root.poller.queues

        result = {"node_name": self.root.nodename, "status": "ok", "currstate": "unknown"}

        for s in self.root.launcher.finished:
            if (not project or s.project == project) and s.job == job:
                result["currstate"] = "finished"
                return result

        for s in spiders:
            if (not project or s.project == project) and s.job == job:
                result["currstate"] = "running"
                return result

        for qname in ([project] if project else queues):
            for x in queues[qname].list():
                if x["_job"] == job:
                    result["currstate"] = "pending"
                    return result

        return result


class ListJobs(WsResource):
    @with_project(required=False)
    def render_GET(self, txrequest, project):
        spiders = self.root.launcher.processes.values()
        queues = self.root.poller.queues

        pending = [
            {"project": qname, "spider": x["name"], "id": x["_job"]}
            for qname in ([project] if project else queues)
            for x in queues[qname].list()
        ]
        running = [
            {
                "project": s.project,
                "spider": s.spider,
                "id": s.job,
                "pid": s.pid,
                "start_time": str(s.start_time),
            }
            for s in spiders
            if not project or s.project == project
        ]
        finished = [
            {
                "project": s.project,
                "spider": s.spider,
                "id": s.job,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "log_url": job_log_url(s),
                "items_url": job_items_url(s),
            }
            for s in self.root.launcher.finished
            if not project or s.project == project
        ]

        return {"node_name": self.root.nodename, "status": "ok",
                "pending": pending, "running": running, "finished": finished}


class DeleteProject(WsResource):
    @with_project()
    def render_POST(self, txrequest, project):
        self._delete_version(project)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        self.root.eggstorage.delete(project, version)
        self.root.update_projects()


class DeleteVersion(DeleteProject):
    @with_project()
    def render_POST(self, txrequest, project):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        version = _get_required_param(args, 'version')[0]
        self._delete_version(project, version)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}
