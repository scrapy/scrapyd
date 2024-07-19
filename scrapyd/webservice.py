from __future__ import annotations

import functools
import json
import sys
import traceback
import uuid
import zipfile
from copy import copy
from io import BytesIO

from twisted.python import log
from twisted.web import error, http, resource

from scrapyd.exceptions import EggNotFoundError, ProjectNotFoundError
from scrapyd.jobstorage import job_items_url, job_log_url
from scrapyd.utils import UtilsCache, get_spider_list, native_stringify_dict


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


class JsonResource(resource.Resource):
    json_encoder = json.JSONEncoder()

    def render(self, txrequest):
        r = resource.Resource.render(self, txrequest)
        return self.encode_object(r, txrequest)

    def encode_object(self, obj, txrequest):
        r = "" if obj is None else self.json_encoder.encode(obj) + "\n"
        txrequest.setHeader("Content-Type", "application/json")
        txrequest.setHeader("Access-Control-Allow-Origin", "*")
        txrequest.setHeader("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, DELETE")
        txrequest.setHeader("Access-Control-Allow-Headers", " X-Requested-With")
        txrequest.setHeader("Content-Length", str(len(r)))
        return r


class WsResource(JsonResource):
    def __init__(self, root):
        JsonResource.__init__(self)
        self.root = root

    def render(self, txrequest):
        try:
            return JsonResource.render(self, txrequest).encode("utf-8")
        except Exception as e:  # noqa: BLE001
            if isinstance(e, error.Error):
                txrequest.setResponseCode(int(e.status))
            if self.root.debug:
                return traceback.format_exc().encode("utf-8")
            log.err()
            message = e.message.decode() if isinstance(e, error.Error) else f"{type(e).__name__}: {e}"
            r = {"node_name": self.root.nodename, "status": "error", "message": message}
            return self.encode_object(r, txrequest).encode("utf-8")

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
        pending = sum(q.count() for q in self.root.scheduler.queues.values())
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

        spider_arguments = {k: v[0] for k, v in native_stringify_dict(copy(txrequest.args), keys_only=False).items()}

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

        if self.root.scheduler.queues[project].remove(lambda x: x["_job"] == job):
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
        projects = list(self.root.scheduler.list_projects())
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
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        try:
            self.root.eggstorage.delete(project, version)
            self.root.update_projects()
        except ProjectNotFoundError as e:
            raise error.Error(code=http.OK, message=b"project '%b' not found" % project.encode()) from e
        except EggNotFoundError as e:
            raise error.Error(code=http.OK, message=b"version '%b' not found" % version.encode()) from e


class DeleteVersion(DeleteProject):
    @param("project")
    @param("version")
    def render_POST(self, txrequest, project, version):
        self._delete_version(project, version)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}
