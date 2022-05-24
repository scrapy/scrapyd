import json
from copy import copy
import traceback
import uuid

try:
    from cStringIO import StringIO as BytesIO
except ImportError:
    from io import BytesIO

from twisted.python import log

from scrapyd.utils import get_spider_list, JsonResource, UtilsCache, native_stringify_dict
from scrapyd.orchestrator_client.api_interfaces.ProjectApi import ProjectApi
from scrapyd.orchestrator_client.api_interfaces.SpiderApi import SpiderApi
from scrapyd.orchestrator_client.api_interfaces.JobApi import JobApi


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

        return {
            "node_name": self.root.nodename,
            "status": "ok",
            "pending": pending,
            "running": running,
            "finished": finished,
        }


class Schedule(WsResource):

    def render_POST(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        settings = args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        version = args.get('_version', '')
        priority = float(args.pop('priority', 0))
        spiders = get_spider_list(project, version=version)
        if spider not in spiders:
            return {"status": "error", "message": "spider '%s' not found" % spider}
        args['settings'] = settings
        jobid = args.pop('jobid', uuid.uuid1().hex)

        """
            Adding job to orchestrator
        """
        try:
            project_api = ProjectApi()
            spider_api = SpiderApi()
            job_api = JobApi()
            project_obj = project_api.get_by_name(project)
            spider_obj = spider_api.get_by_name(spider)

            job_obj = job_api.add(project_obj['id'], spider_obj['id'], json.dumps(settings))
            args['_job'] = str(job_obj['id'])

        except Exception as e:
            log(str(e))

        log.msg(f"Scheduled job with id {str(args['_job'])} for project {str(project)} running on spider {str(spider)}")
        self.root.scheduler.schedule(project, spider, priority=priority, **args)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": args['_job']}



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
            if s.project == project and s.job == jobid:
                s.transport.signalProcess(signal)
                prevstate = "running"

        """
            UPDATE JOB STATE IN ORCHESTRATOR
        """
        try:
            job_api = JobApi()
            job_api.update(jobid, state="CANCELED")
        except Exception as e:
            log.msg(str(e))
        return {"node_name": self.root.nodename, "status": "ok", "prevstate": prevstate}


class AddVersion(WsResource):

    def render_POST(self, txrequest):
        eggf = BytesIO(txrequest.args.pop(b'egg')[0])
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        version = args['version'][0]
        self.root.eggstorage.put(eggf, project, version)
        spiders = get_spider_list(project, version=version)
        """
        Add new project / update project in orchestrator's database
        """
        log.msg(f"Added project {str(project)} with version {str(version)} and spiders {str(spiders)}")

        self.root.update_projects()
        UtilsCache.invalid_cache(project)

        try:
            project_api = ProjectApi()
            spider_api = SpiderApi()
            find_proj = project_api.get_by_name(project)
            if find_proj == {}:
                orch_project = project_api.add(project, version)
                for spider in spiders:
                    spider_api.add(orch_project['id'], spider)
            else:
                project_api.update(project, version=version)
                available_spiders = spider_api.get_all_spiders_by_project_name(project)
                if set(available_spiders) != set(spiders):
                    for spider in available_spiders:
                        if spider not in spiders:
                            spider_obj = spider_api.get_by_name(spider)
                            spider_api.delete(spider_obj['id'])
                    for spider in spiders:
                        if spider not in available_spiders:
                            spider_api.add(find_proj['id'], spider)
        except Exception as e:
            log.msg(str(e))

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
        project = args.get('project', [None])[0]
        spiders = self.root.launcher.processes.values()
        queues = self.root.poller.queues
        pending = [
            {"project": qname, "spider": x["name"], "id": x["_job"]}
            for qname in (queues if project is None else [project])
            for x in queues[qname].list()
        ]
        running = [
            {
                "project": s.project,
                "spider": s.spider,
                "id": s.job, "pid": s.pid,
                "start_time": str(s.start_time),
            } for s in spiders if project is None or s.project == project
        ]
        finished = [
            {
                "project": s.project,
                "spider": s.spider, "id": s.job,
                "start_time": str(s.start_time),
                "end_time": str(s.end_time)
            } for s in self.root.launcher.finished
            if project is None or s.project == project
        ]
        return {"node_name": self.root.nodename, "status": "ok",
                "pending": pending, "running": running, "finished": finished}


class DeleteProject(WsResource):

    def render_POST(self, txrequest):
        args = native_stringify_dict(copy(txrequest.args), keys_only=False)
        project = args['project'][0]
        """
        DELETE PROJECT FROM ORCHESTRATOR'S DATABASE
        """
        try:
            project_api = ProjectApi()
            project_obj = project_api.get_by_name(project)
            project_api.delete(project_obj['id'])
        except Exception as e:
            log.msg(str(e))

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
        """
                DELETE PROJECT VERSION FROM ORCHESTRATOR'S DATABASE
        """
        self._delete_version(project, version)
        UtilsCache.invalid_cache(project)
        return {"node_name": self.root.nodename, "status": "ok"}
