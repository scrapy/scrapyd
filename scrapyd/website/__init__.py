import posixpath
import pkg_resources

from datetime import datetime

from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object
from scrapyd.interfaces import IPoller, IEggStorage, ISpiderScheduler

class Logs(static.File):
    def __init__(self, root, *args, **kwargs):
        static.File.__init__(self, 
            root if isinstance(root, basestring) else root.config.get('logs_dir'), "text/plain", *args, **kwargs)
    
class Items(static.File):
    def __init__(self, root, *args, **kwargs):
        static.File.__init__(self, 
            root if isinstance(root, basestring) else root.config.get('items_dir'), "application/json", *args, **kwargs)
    
class Jobs(resource.Resource):
    isLeaf = True
    
    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render(self, txrequest):
        s = "<html><head><title>Scrapyd</title></title>"
        s += "<body>"
        s += "<h1>Jobs</h1>"
        s += "<p><a href='..'>Go back</a></p>"
        s += "<table border='1'>"
        s += "<th>Project</th><th>Spider</th><th>Job</th><th>PID</th><th>Runtime</th><th>Log</th><th>Items</th>"
        s += "<tr><th colspan='7' style='background-color: #ddd'>Pending</th></tr>"
        for project, queue in self.root.poller.queues.items():
            for m in queue.list():
                s += "<tr>"
                s += "<td>%s</td>" % project
                s += "<td>%s</td>" % str(m['name'])
                s += "<td>%s</td>" % str(m['_job'])
                s += "</tr>"
        s += "<tr><th colspan='7' style='background-color: #ddd'>Running</th></tr>"
        for p in self.root.launcher.processes.values():
            s += "<tr>"
            for a in ['project', 'spider', 'job', 'pid']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td>%s</td>" % (datetime.now() - p.start_time)
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
            s += "</tr>"
        s += "<tr><th colspan='7' style='background-color: #ddd'>Finished</th></tr>"
        for p in self.root.launcher.finished:
            s += "<tr>"
            for a in ['project', 'spider', 'job']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td></td>"
            s += "<td>%s</td>" % (p.end_time - p.start_time)
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
            s += "</tr>"
        s += "</table>"
        s += "</body>"
        s += "</html>"
        return s

class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)

        self.app = app
        self.config = config

        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')

        self.services = config.items('services', ())
        for path, resource_class_name in self.services:
          servCls = load_object(resource_class_name)
          self.putChild(path, servCls(self))
        self.default_child = self.children.get("default")

        self.update_projects()

    def getChild(self, name, request):
        if self.default_child:
            return self.default_child
        return self
    def render(self, request, **kwargs):
        request.setResponseCode(404)
        return "No default service"

    def update_projects(self):
        self.poller.update_projects()
        self.scheduler.update_projects()

    @property
    def launcher(self):
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed('launcher')

    @property
    def scheduler(self):
        return self.app.getComponent(ISpiderScheduler)

    @property
    def eggstorage(self):
        return self.app.getComponent(IEggStorage)

    @property
    def poller(self):
        return self.app.getComponent(IPoller)

