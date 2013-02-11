import posixpath
import pkg_resources

from datetime import datetime

from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object

from .interfaces import IPoller, IEggStorage, ISpiderScheduler

""" FRONTEND specifies the front end directory 

    frontend is None: no frontend
    frontend is "": frontend
    frontend is "htdocs": folder containing the htdocs module

"""
FRONTEND = None

class Frontend(resource.Resource):

    def __init__(self, root=None, path=None):
        self.path = path
        self.root = root
    
    @classmethod
    def from_path(cls, root, path):
        return cls(root, path)

    def render(self, txrequest):
        name = txrequest.sitepath or "index.html"

        path = posixpath.join(self.root.frontend.path, name)
        if path:
            return static.File(path).render(txrequest)
        return WithoutFrontend(self).render(txrequest)
    
class Root(resource.Resource):

    def __init__(self, config, app, frontend=FRONTEND):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')

        if frontend is None:
            frontend_path = config.get('frontend_path', 'frontend')
            if isinstance(frontend_path, basestring):
                frontend_path = pkg_resources.resource_filename("scrapyd", frontend_path)
                frontend = Frontend.from_path(self, frontend_path)
            
            self.frontend = frontend

        logsdir = config.get('logs_dir')
        itemsdir = config.get('items_dir')
        self.app = app

        self.putChild('logs', static.File(logsdir, 'text/plain'))
        self.putChild('items', static.File(itemsdir, 'text/plain'))
        self.putChild('jobs', Jobs(self))

        self.putChild('', Frontend(self))

        # self.putChild('frontend', Frontend(self))

        services = config.items('services', ())
        for servName, servClsName in services:
          servCls = load_object(servClsName)
          self.putChild(servName, servCls(self))
        self.update_projects()

    def getChild(self, name, request):
        if name == "":
            name == "index.html"

        path = posixpath.join(self.frontend.path, name)
        if posixpath.exists(path):
            return static.File(path)

        return WithoutFrontend(self)

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


class WithoutFrontend(resource.Resource):
    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render(self, txrequest):
        txrequest.setResponseCode(404)
        
        return """<html><head><title>No frontend</title><h1>No frontend</h1>
        <p>Add a frontend or create 'without_frontend.html' in your frontend</p>
        </body>
        </html>
        """
        #else:
        #    return """<html><head><title>No frontend</title><h1>No frontend</h1>
        #    <p>This server has no frontend</p>
        #    </body>
        #    </html>
        #    """

class Jobs(resource.Resource):

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
