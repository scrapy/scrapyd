import traceback
import uuid
from cStringIO import StringIO

from twisted.python import log

from .utils import get_spider_list, JsonResource, UtilsCache

class WsResource(JsonResource):

    def __init__(self, root):
        JsonResource.__init__(self)
        self.root = root

    def render(self, txrequest):
        try:
            return JsonResource.render(self, txrequest)
        except Exception, e:
            if self.root.debug:
                return traceback.format_exc()
            log.err()
            r = {"node_name": self.root.nodename, "status": "error", "message": str(e)}
            return self.render_object(r, txrequest)

class Schedule(WsResource):

    def render_POST(self, txrequest):
        settings = txrequest.args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in txrequest.args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        spiders = get_spider_list(project)
        if not spider in spiders:
            return {"status": "error", "message": "spider '%s' not found" % spider}
        args['settings'] = settings
        jobid = uuid.uuid1().hex
        args['_job'] = jobid
        self.root.scheduler.schedule(project, spider, **args)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}

class Cancel(WsResource):

    def render_POST(self, txrequest):
        args = dict((k, v[0]) for k, v in txrequest.args.items())
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
        project = txrequest.args['project'][0]
        version = txrequest.args['version'][0]
        eggf = StringIO(txrequest.args['egg'][0])
        self.root.eggstorage.put(eggf, project, version)
        spiders = get_spider_list(project)
        self.root.update_projects()
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok", "project": project, "version": version, \
            "spiders": len(spiders)}

class ListProjects(WsResource):

    def render_GET(self, txrequest):
        projects = self.root.scheduler.list_projects()
        return {"node_name": self.root.nodename, "status": "ok", "projects": projects}

class ListVersions(WsResource):

    def render_GET(self, txrequest):
        project = txrequest.args['project'][0]
        versions = self.root.eggstorage.list(project)
        return {"node_name": self.root.nodename, "status": "ok", "versions": versions}

class ListSpiders(WsResource):

    def render_GET(self, txrequest):
        project = txrequest.args['project'][0]
        spiders = get_spider_list(project, runner=self.root.runner)
        return {"node_name": self.root.nodename, "status": "ok", "spiders": spiders}

class ListJobs(WsResource):

    def render_GET(self, txrequest):
        project = txrequest.args['project'][0]
        spiders = self.root.launcher.processes.values()
        running = [{"id": s.job, "spider": s.spider,
            "start_time": s.start_time.isoformat(' ')} for s in spiders if s.project == project]
        queue = self.root.poller.queues[project]
        pending = [{"id": x["_job"], "spider": x["name"]} for x in queue.list()]
        finished = [{"id": s.job, "spider": s.spider,
            "start_time": s.start_time.isoformat(' '),
            "end_time": s.end_time.isoformat(' ')} for s in self.root.launcher.finished
            if s.project == project]
        return {"node_name": self.root.nodename, "status":"ok", "pending": pending, "running": running, "finished": finished}

class DeleteProject(WsResource):

    def render_POST(self, txrequest):
        project = txrequest.args['project'][0]
        self._delete_version(project)
        return {"node_name": self.root.nodename, "status": "ok"}

    def _delete_version(self, project, version=None):
        self.root.eggstorage.delete(project, version)
        self.root.update_projects()

class DeleteVersion(DeleteProject):

    def render_POST(self, txrequest):
        project = txrequest.args['project'][0]
        version = txrequest.args['version'][0]
        self._delete_version(project, version)
        return {"node_name": self.root.nodename, "status": "ok"}
