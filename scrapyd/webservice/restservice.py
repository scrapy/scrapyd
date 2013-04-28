"""This module provides RESTful API to Scrapyd


"""

import traceback
import uuid
from cStringIO import StringIO

from scrapy.utils.misc import load_object

HAS_JSON = False
try:
    import json
    HAS_JSON = True
except ImportError, exc:
    try:
        import simplejson as json
        HAS_JSON = True
    except ImportError, exc:
        print exc
    
HAS_XML = False
try:
    from xml.etree import ElementTree
    HAS_XML = True
except ImportError, exc:
    print exc

HAS_YAML = False
try:
    import yaml
    HAS_YAML = True
except ImportError, exc:
    print exc

import zope.interface

from twisted.web import resource
from twisted.python import log
from twisted.internet import defer

import corepost
from corepost.web import route, RESTResource
from corepost.filters import IRequestFilter, IResponseFilter
from corepost.enums import Http, MediaType, HttpHeader

from scrapyd import __version__

from scrapyd.utils import get_spider_list

class ServerFilter(object):
    """Set the 'Server' response header""" 
    zope.interface.implements(IResponseFilter)

    def filterResponse(self, request, response): 
        response.headers["Server"] = "Scrapyd/" + __version__

class BaseRESTResource(RESTResource):
    def __init__(self, root, services=(), filters=None, **kwargs):
        self.root = root
        filters = filters or (ServerFilter(),)
        RESTResource.__init__(self, services=services, filters=filters, **kwargs)

class BaseRESTService():
    def __init__(self, root):
        self.root = root

class ProjectsRESTService(BaseRESTService):

    get_proj_info = lambda self, project:(project, {
                    "spiders": get_spider_list(project, 
                                                runner=self.root.runner), 
                    "versions": self.root.eggstorage.list(project)
                },)


    @route("/", Http.GET)
    #@defer.inlineCallbacks
    def get__all(self, request, **kwargs):
        return dict(map(self.get_proj_info, 
            self.root.scheduler.list_projects()))

    @route("/<pk>", Http.GET)
    #@defer.inlineCallbacks
    def get(self, request, pk, **kwargs):
        if pk not in self.root.scheduler.list_projects():
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})
        return self.get_proj_info(pk)

    @route("/", Http.PUT)
    def post(self, request, project, version, egg, **kwargs):
        eggf = StringIO(egg)
        self.root.eggstorage.put(eggf, project, version)
        spiders = get_spider_list(project)
        self.root.update_projects()
        return {"status": "ok", "project": project, "version": version, \
            "spiders": len(spiders)}
    
    #@route("/project/<projectid>", Http.POST)
    #def get(self, request, projectid, **kwargs):
    #    return corepost.Response(501, entity="Not implemented",
    #         headers={"Content-Type":"text/plain"})

    @route("/<pk>/spiders", Http.GET)
    def get_spiders(self, request, pk, **kwargs):
        if pk not in self.root.scheduler.list_projects():
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})
        return get_spider_list(pk, runner=self.root.runner)
    
    @route("/<pk>/versions", Http.GET)
    def get_versions(self, request, pk, **kwargs):
        if pk not in self.root.scheduler.list_projects():
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})
        return self.root.eggstorage.list(pk)
    
    @route("/<pk>/versions/<version>", Http.DELETE)
    def delete_versions(self, request, project, version, **kwargs):
        return self.delete(request, pk, version, **kwargs)

    @route("/<pk>", Http.DELETE)
    def delete(self, request, pk, version=None, **kwargs):
        if pk not in self.root.scheduler.list_projects():
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})
        if version and (version not in self.root.eggstorage.list(pk)):
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})

        self.root.eggstorage.delete(pk, version)
        self.root.update_projects()
        
        return {"status": "ok"}

class JobsRESTService(BaseRESTService):

    @route("/", Http.PUT)
    #@defer.inlineCallbacks
    def put(self, request, project, spider, setting=[], **kwargs):
        if project not in self.root.scheduler.list_projects():
            return corepost.Response(404, entity="Not found",
                 headers={"Content-Type":"text/plain"})
        settings = request.args.get("setting", [])
        if len(settings):
            kwargs['settings'] = dict(x.split('=', 1) for x in settings)
        jobid = uuid.uuid1().hex
        kwargs['_job'] = jobid
        self.root.scheduler.schedule(project, spider, **kwargs)
        self.root.poller.poll()
        return {"status": "ok", "jobid": jobid}

    #@route("/<pk>", Http.POST)
    #def update(self, request, pk, **kwargs):
    #    return corepost.Response(501, entity="Not implemented",
    #         headers={"Content-Type":"text/plain"})

    @route("/", Http.GET)
    #@defer.inlineCallbacks
    def get__all(self, request, project=None, **kwargs):
        """
        This commands lists current jobs
        
        TODO! 

            * filters: By Status: status=="pending",...
            * Pagination: Implement Range Header in corepost for a slice

        """

        #project = txrequest.args['project'][0]
        spiders = self.root.launcher.processes.values()
        running = pending = finished = ()

        jobs = []
        
        for s in spiders:
            job = {"id": s.job, "spider": s.spider, 
                "project": s.project, 
                "start_time": s.start_time.isoformat(' '), 
                "status":"running"}
            #running = yield job
            jobs.append(job)
        
        for project in self.root.scheduler.list_projects():
            queue = self.root.poller.queues[project]
            for s in queue.list():
                #if (not project) or s.project == project:
                job = {"id": s["_job"], 
                    "spider": s["name"],
                    "project": project,
                    "status":"pending"}
                #pending = yield job
                jobs.append(job)
        
        for s in self.root.launcher.finished.__reversed__():
            job = {"id": s.job, 
                "spider": s.spider,
                "project": s.project,
                "start_time": s.start_time.isoformat(' '),
                "end_time": s.end_time.isoformat(' '), "status":"finished"}
            #finished = yield job
            jobs.append(job)

        return {"status":"ok", "jobs": jobs}
        #defer.returnValue(
        #    {"status":"ok", "jobs": jobs})

    @route("/<pk>", Http.GET)
    def get(self, request, pk, **kwargs):
        return corepost.Response(501, entity="Not implemented",
             headers={"Content-Type":"text/plain"})

    @route("/<pk>/items", Http.GET)
    def get_read(self, request, pk, **kwargs):
        basedir = self.root.config.get('items_dir')
        return corepost.Response(501, entity="Not implemented",
             headers={"Content-Type":"text/plain"})

    @route("/<pk>/logs", Http.GET)
    def get_read(self, request, pk, **kwargs):
        basedir = self.root.config.get('logs_dir')
        return corepost.Response(501, entity="Not implemented",
             headers={"Content-Type":"text/plain"})
    

    @route("/<pk>", Http.DELETE)
    def delete(self, request, pk, **kwargs):
        """
        This commands acts as a delete and cancels the task if 
        in pending or running state
        
        curl -v -X DELETE http://localhost:6800/job/JOBID
        
        
        """
        signal = kwargs.get('signal', 'TERM')

        x = self.job_from_id(pk)
        if x is None:
            return corepost.Response(410, entity="Job not available",
                 headers={"Content-Type":"text/plain"})

        project, queue, job = x
        c = queue.remove(lambda x: x["_job"] == pk)

        prevstate = "unknown"
        if c:
            prevstate = "pending"
        # also kill the job if running
        spiders = self.root.launcher.processes.values()
        for s in spiders:
            if s.job == pk:
                s.transport.signalProcess(signal)
                prevstate = "running"

        return {"status":"ok", "prevstate": prevstate}

    def job_from_id(self, jobid):
        for project in self.root.scheduler.list_projects():
            queue = self.root.poller.queues[project]
            for job in queue.list():
                if job.get("_job", None) == jobid:
                    return project, queue, job 
    

class ScrapydRESTService(BaseRESTService):

    @route("/ping", Http.GET)
    def pong(self, request, **kwargs):
        return "pong"

    @route("/", Http.GET)
    def get__all(self, request, **kwargs):
        return {"status": "ok", 
            "server": {"version":__version__}}

    @route("/config", Http.GET)
    def get_config(self, request, pk="scrapyd", **kwargs):
        return dict(self.root.config.items(pk))

class ProjectsResource(BaseRESTResource):
    def __init__(self, root, services=(), **kwargs):
        services = (ProjectsRESTService(root),)
        BaseRESTResource.__init__(self, root, services=services, **kwargs)

class JobsResource(BaseRESTResource):
    def __init__(self, root, services=(), filters=(), **kwargs):
        services = (JobsRESTService(root),)
        BaseRESTResource.__init__(self, root, services=services, **kwargs)

class ScrapydResource(BaseRESTResource):
    def __init__(self, root, services=(), filters=(), **kwargs):
        services = (ScrapydRESTService(root),)
        BaseRESTResource.__init__(self, root, services=services, **kwargs)

class ApiResource(resource.Resource):
    name = "api_v1"
    
    def __init__(self, root, **kwargs):
        resource.Resource.__init__(self, **kwargs)
        self.root = root
        for path, resource_class_name in \
            root.config.items(kwargs.get("name", self.name), ()):
          servCls = load_object(resource_class_name)
          self.putChild(path, servCls(root))
