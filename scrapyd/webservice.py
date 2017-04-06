from copy import copy
import traceback
import uuid
try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from twisted.python import log

from .utils import get_spider_list, JsonResource, UtilsCache, native_stringify_dict

class WsResource(JsonResource):

    def __init__(self, root):
        JsonResource.__init__(self)
        self.root = root

    def render(self, txrequest):
        try:
            return JsonResource.render(self, txrequest).encode('utf-8')
        except Exception as e:
            if self.root.debug:
                return traceback.format_exc().encode('utf-8')
            log.err()
            r = {"node_name": self.root.nodename, "status": "error", "message": str(e)}
            return self.render_object(r, txrequest).encode('utf-8')

class DaemonStatus(WsResource):

    def render_GET(self, txrequest):
        pending = sum(q.count() for q in self.root.poller.queues.values())
        running = len(self.root.launcher.processes)
        finished = len(self.root.launcher.finished)

        return {"node_name": self.root.nodename, "status":"ok", "pending": pending, "running": running, "finished": finished}


class Schedule(WsResource):

    def render_POST(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        settings = args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        version = args.get('_version', '')
        spiders = get_spider_list(project, version=version)
        if not spider in spiders:
            return {"status": "error", "message": "spider '%s' not found" % spider}
        args['settings'] = settings
        jobid = args.pop('jobid', uuid.uuid1().hex)
        args['_job'] = jobid
        self.root.scheduler.schedule(project, spider, **args)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}

class Cancel(WsResource):

    def render_POST(self, txrequest):
        args = dict((k, v[0])
                    for k, v in native_stringify_dict(copy(txrequest.args),
                                    keys_only=False).items())
        project = args['project']
        jobid = args['job']
        signal = args.get('signal', 'TERM')
        prevstate = None
        queue = self.root.poller.queues[project]
        c = queue.remove(lambda x: x["_job"] == jobid)
        if c:
            prevstate = "pending"
        spiders = self.root.launcher.processes.values()
        for s in spiders:
            if s.job == jobid:
                s.transport.signalProcess(signal)
                prevstate = "running"
        return {"node_name": self.root.nodename, "status": "ok", "prevstate": prevstate}

class AddVersion(WsResource):

    def render_POST(self, txrequest):
        project = txrequest.args[b'project'][0].decode('utf-8')
        version = txrequest.args[b'version'][0].decode('utf-8')
        eggf = BytesIO(txrequest.args[b'egg'][0])
        self.root.eggstorage.put(eggf, project, version)
        spiders = get_spider_list(project, version=version)
        self.root.update_projects()
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok", "project": project, "version": version, \
            "spiders": len(spiders)}

class ListProjects(WsResource):

    def render_GET(self, txrequest):
        projects = list(self.root.scheduler.list_projects())
        return {"node_name": self.root.nodename, "status": "ok", "projects": projects}

class ListVersions(WsResource):

    def render_GET(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        versions = self.root.eggstorage.list(project)
        return {"node_name": self.root.nodename, "status": "ok", "versions": versions}

class ListSpiders(WsResource):

    def render_GET(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        version = args.get('_version', [''])[0]
        spiders = get_spider_list(project, runner=self.root.runner, version=version)
        return {"node_name": self.root.nodename, "status": "ok", "spiders": spiders}

class ListJobs(WsResource):

    def render_GET(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        spiders = self.root.launcher.processes.values()
        running = [{"id": s.job, "spider": s.spider, "pid": s.pid,
                    "start_time": s.start_time.isoformat(' ')}
                   for s in spiders if s.project == project]
        queue = self.root.poller.queues[project]
        pending = [{"id": x["_job"], "spider": x["name"]} for x in queue.list()]
        finished = [{"id": s.job, "spider": s.spider,
            "start_time": s.start_time.isoformat(' '),
            "end_time": s.end_time.isoformat(' ')} for s in self.root.launcher.finished
            if s.project == project]
        return {"node_name": self.root.nodename, "status":"ok", "pending": pending, "running": running, "finished": finished}

class DeleteProject(WsResource):

    def render_POST(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        self._delete_version(project)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        self.root.eggstorage.delete(project, version)
        self.root.update_projects()

class DeleteVersion(DeleteProject):

    def render_POST(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        version = args['version'][0]
        self._delete_version(project, version)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}
