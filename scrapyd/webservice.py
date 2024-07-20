from __future__ import annotations

import functools
import json
import os
import sys
import traceback
import uuid
import zipfile
from copy import copy
from io import BytesIO
from subprocess import PIPE, Popen
from typing import ClassVar

from twisted.python import log
from twisted.web import error, http, resource

from scrapyd.config import Config
from scrapyd.exceptions import EggNotFoundError, ProjectNotFoundError, RunnerError
from scrapyd.sqlite import JsonSqliteDict
from scrapyd.utils import job_items_url, job_log_url, native_stringify_dict


def param(
    decoded: str,
    *,
    dest: str | None = None,
    required: bool = True,
    default=None,
    multiple: bool = False,
    type=str,  # noqa: A002 like Click
):
    encoded = decoded.encode()
    if dest is None:
        dest = decoded
    if callable(default):
        default = default()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, txrequest, *args, **kwargs):
            if encoded not in txrequest.args:
                if required:
                    raise error.Error(code=http.OK, message=b"'%b' parameter is required" % encoded)

                value = default
            else:
                values = (value.decode() if type is str else type(value) for value in txrequest.args.pop(encoded))
                value = list(values) if multiple else next(values)

            kwargs[dest] = value

            return func(self, txrequest, *args, **kwargs)

        return wrapper

    return decorator


def get_spider_list(project, runner=None, pythonpath=None, version=None):
    """Return the spider list from the given project, using the given runner"""

    # UtilsCache uses JsonSqliteDict, which encodes the project's value as JSON, but JSON allows only string keys,
    # so the stored dict will have a "null" key, instead of a None key.
    if version is None:
        version = ""

    if "cache" not in get_spider_list.__dict__:
        get_spider_list.cache = UtilsCache()
    try:
        return get_spider_list.cache[project][version]
    except KeyError:
        pass

    if runner is None:
        runner = Config().get("runner")

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "UTF-8"
    env["SCRAPY_PROJECT"] = project
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    if version:
        env["SCRAPYD_EGG_VERSION"] = version
    pargs = [sys.executable, "-m", runner, "list", "-s", "LOG_STDOUT=0"]
    proc = Popen(pargs, stdout=PIPE, stderr=PIPE, env=env)
    out, err = proc.communicate()
    if proc.returncode:
        msg = err or out or ""
        msg = msg.decode("utf8")
        raise RunnerError(msg)

    spiders = out.decode("utf-8").splitlines()
    try:
        project_cache = get_spider_list.cache[project]
        project_cache[version] = spiders
    except KeyError:
        project_cache = {version: spiders}
    get_spider_list.cache[project] = project_cache

    return spiders


class UtilsCache:
    # array of project name that need to be invalided
    invalid_cached_projects: ClassVar = []

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

    def __repr__(self):
        return f"UtilsCache(cache_manager={self.cache_manager!r})"


class WsResource(resource.Resource):
    json_encoder = json.JSONEncoder()

    def __init__(self, root):
        super().__init__()
        self.root = root

    def render(self, txrequest):
        try:
            obj = super().render(txrequest)
        except Exception as e:  # noqa: BLE001
            log.err()

            if isinstance(e, error.Error):
                txrequest.setResponseCode(int(e.status))

            if self.root.debug:
                return traceback.format_exc().encode()

            message = e.message.decode() if isinstance(e, error.Error) else f"{type(e).__name__}: {e}"
            obj = {"node_name": self.root.nodename, "status": "error", "message": message}

        content = b"" if obj is None else self.json_encoder.encode(obj).encode() + b"\n"
        txrequest.setHeader("Content-Type", "application/json")
        txrequest.setHeader("Access-Control-Allow-Origin", "*")
        txrequest.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE")
        txrequest.setHeader("Access-Control-Allow-Headers", " X-Requested-With")
        txrequest.setHeader("Content-Length", str(len(content)))
        return content

    def render_OPTIONS(self, txrequest):
        methods = ["OPTIONS", "HEAD"]
        if hasattr(self, "render_GET"):
            methods.append("GET")
        if hasattr(self, "render_POST"):
            methods.append("POST")
        txrequest.setHeader("Allow", ", ".join(methods))
        txrequest.setResponseCode(http.NO_CONTENT)


class DaemonStatus(WsResource):
    def render_GET(self, txrequest):
        pending = sum(queue.count() for queue in self.root.scheduler.queues.values())
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
    @param("project")
    @param("spider")
    @param("_version", dest="version", required=False, default=None)
    # See https://github.com/scrapy/scrapyd/pull/215
    @param("jobid", required=False, default=lambda: uuid.uuid1().hex)
    @param("priority", required=False, default=0, type=float)
    @param("setting", required=False, default=list, multiple=True)
    def render_POST(self, txrequest, project, spider, version, jobid, priority, setting):
        if self.root.eggstorage.get(project, version) == (None, None):
            if version:
                raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode())
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        spiders = get_spider_list(project, version=version, runner=self.root.runner)
        if spider not in spiders:
            raise error.Error(code=http.OK, message=b"spider '%b' not found" % spider.encode())

        spider_arguments = {k: v[0] for k, v in native_stringify_dict(copy(txrequest.args)).items()}

        self.root.scheduler.schedule(
            project,
            spider,
            priority=priority,
            settings=dict(s.split("=", 1) for s in setting),
            version=version,
            _job=jobid,
            **spider_arguments,
        )
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}


class Cancel(WsResource):
    @param("project")
    @param("job")
    # Instead of os.name, use sys.platform, which disambiguates Cygwin, which implements SIGINT not SIGBREAK.
    # https://cygwin.com/cygwin-ug-net/kill.html
    # https://github.com/scrapy/scrapy/blob/06f9c28/tests/test_crawler.py#L886
    @param("signal", required=False, default="INT" if sys.platform != "win32" else "BREAK")
    def render_POST(self, txrequest, project, job, signal):
        if project not in self.root.scheduler.queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        prevstate = None

        if self.root.scheduler.queues[project].remove(lambda message: message["_job"] == job):
            prevstate = "pending"

        spiders = self.root.launcher.processes.values()
        for s in spiders:
            if s.project == project and s.job == job:
                s.transport.signalProcess(signal)
                prevstate = "running"
                break

        return {"node_name": self.root.nodename, "status": "ok", "prevstate": prevstate}


class AddVersion(WsResource):
    @param("project")
    @param("version")
    @param("egg", type=bytes)
    def render_POST(self, txrequest, project, version, egg):
        if not zipfile.is_zipfile(BytesIO(egg)):
            raise error.Error(
                code=http.OK, message=b"egg is not a ZIP file (if using curl, use egg=@path not egg=path)"
            )

        self.root.eggstorage.put(BytesIO(egg), project, version)
        spiders = get_spider_list(project, version=version, runner=self.root.runner)
        self.root.update_projects()
        UtilsCache.invalid_cache(project)
        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "project": project,
            "version": version,
            "spiders": len(spiders),
        }


class ListProjects(WsResource):
    def render_GET(self, txrequest):
        projects = self.root.scheduler.list_projects()
        return {"node_name": self.root.nodename, "status": "ok", "projects": projects}


class ListVersions(WsResource):
    @param("project")
    def render_GET(self, txrequest, project):
        versions = self.root.eggstorage.list(project)
        return {"node_name": self.root.nodename, "status": "ok", "versions": versions}


class ListSpiders(WsResource):
    @param("project")
    @param("_version", dest="version", required=False, default=None)
    def render_GET(self, txrequest, project, version):
        if self.root.eggstorage.get(project, version) == (None, None):
            if version:
                raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode())
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        spiders = get_spider_list(project, version=version, runner=self.root.runner)

        return {"node_name": self.root.nodename, "status": "ok", "spiders": spiders}


class Status(WsResource):
    @param("job")
    @param("project", required=False)
    def render_GET(self, txrequest, job, project):
        spiders = self.root.launcher.processes.values()
        queues = self.root.scheduler.queues

        if project is not None and project not in queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        result = {"node_name": self.root.nodename, "status": "ok", "currstate": None}

        for s in self.root.launcher.finished:
            if (project is None or s.project == project) and s.job == job:
                result["currstate"] = "finished"
                return result

        for s in spiders:
            if (project is None or s.project == project) and s.job == job:
                result["currstate"] = "running"
                return result

        for qname in queues if project is None else [project]:
            for x in queues[qname].list():
                if x["_job"] == job:
                    result["currstate"] = "pending"
                    return result

        return result


class ListJobs(WsResource):
    @param("project", required=False)
    def render_GET(self, txrequest, project):
        spiders = self.root.launcher.processes.values()
        queues = self.root.scheduler.queues

        if project is not None and project not in queues:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode())

        pending = [
            {"project": qname, "spider": x["name"], "id": x["_job"]}
            for qname in (queues if project is None else [project])
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
            if project is None or s.project == project
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
            if project is None or s.project == project
        ]

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished,
        }


class DeleteProject(WsResource):
    @param("project")
    def render_POST(self, txrequest, project):
        self._delete_version(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        try:
            self.root.eggstorage.delete(project, version)
        except ProjectNotFoundError as e:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode()) from e
        except EggNotFoundError as e:
            raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode()) from e
        else:
            self.root.update_projects()
            UtilsCache.invalid_cache(project)


class DeleteVersion(DeleteProject):
    @param("project")
    @param("version")
    def render_POST(self, txrequest, project, version):
        self._delete_version(project, version)
        return {"node_name": self.root.nodename, "status": "ok"}
