from datetime import datetime

import socket

from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object

from .interfaces import IPoller, IEggStorage, ISpiderScheduler

from six.moves.urllib.parse import urlparse

class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')
        logsdir = config.get('logs_dir')
        itemsdir = config.get('items_dir')
        local_items = itemsdir and (urlparse(itemsdir).scheme.lower() in ['', 'file'])
        self.app = app
        self.nodename = config.get('node_name', socket.gethostname())
        self.putChild(b'', Home(self, local_items))
        if logsdir:
            self.putChild(b'logs', static.File(logsdir.encode('ascii', 'ignore'), 'text/plain'))
        if local_items:
            self.putChild(b'items', static.File(itemsdir, 'text/plain'))
        self.putChild(b'jobs', Jobs(self, local_items))
        services = config.items('services', ())
        for servName, servClsName in services:
          servCls = load_object(servClsName)
          self.putChild(servName.encode('utf-8'), servCls(self))
        self.update_projects()

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


class Home(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render_GET(self, txrequest):
        vars = {
            'projects': ', '.join(self.root.scheduler.list_projects())
        }
        s = """
<html>
<head><title>Scrapyd</title></head>
<body>
<h1>Scrapyd</h1>
<p>Available projects: <b>%(projects)s</b></p>
<ul>
<li><a href="/jobs">Jobs</a></li>
""" % vars
        if self.local_items:
            s += '<li><a href="/items/">Items</a></li>'
        s += """
<li><a href="/logs/">Logs</a></li>
<li><a href="http://scrapyd.readthedocs.org/en/latest/">Documentation</a></li>
</ul>

<h2>How to schedule a spider?</h2>

<p>To schedule a spider you need to use the API (this web UI is only for
monitoring)</p>

<p>Example using <a href="http://curl.haxx.se/">curl</a>:</p>
<p><code>curl http://localhost:6800/schedule.json -d project=default -d spider=somespider</code></p>

<p>For more information about the API, see the <a href="http://scrapyd.readthedocs.org/en/latest/">Scrapyd documentation</a></p>
</body>
</html>
""" % vars
        return s.encode('utf-8')

class Jobs(resource.Resource):

    def __init__(self, root, local_items):
        resource.Resource.__init__(self)
        self.root = root
        self.local_items = local_items

    def render(self, txrequest):
        cols = 8
        s = "<html><head><title>Scrapyd</title></head>"
        s += "<body>"
        s += "<h1>Jobs</h1>"
        s += "<p><a href='..'>Go back</a></p>"
        s += "<table border='1'>"
        s += "<tr><th>Project</th><th>Spider</th><th>Job</th><th>PID</th><th>Start</th><th>Runtime</th><th>Finish</th><th>Log</th>"
        if self.local_items:
            s += "<th>Items</th>"
            cols = 9
        s += "</tr>"
        s += "<tr><th colspan='%s' style='background-color: #ddd'>Pending</th></tr>" % cols
        for project, queue in self.root.poller.queues.items():
            for m in queue.list():
                s += "<tr>"
                s += "<td>%s</td>" % project
                s += "<td>%s</td>" % str(m['name'])
                s += "<td>%s</td>" % str(m['_job'])
                s += "</tr>"
        s += "<tr><th colspan='%s' style='background-color: #ddd'>Running</th></tr>" % cols
        for p in self.root.launcher.processes.values():
            s += "<tr>"
            for a in ['project', 'spider', 'job', 'pid']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (datetime.now().replace(microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td></td>"
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
            s += "</tr>"
        s += "<tr><th colspan='%s' style='background-color: #ddd'>Finished</th></tr>" % cols
        for p in self.root.launcher.finished:
            s += "<tr>"
            for a in ['project', 'spider', 'job']:
                s += "<td>%s</td>" % getattr(p, a)
            s += "<td></td>"
            s += "<td>%s</td>" % p.start_time.replace(microsecond=0)
            s += "<td>%s</td>" % (p.end_time.replace(microsecond=0) - p.start_time.replace(microsecond=0))
            s += "<td>%s</td>" % p.end_time.replace(microsecond=0)
            s += "<td><a href='/logs/%s/%s/%s.log'>Log</a></td>" % (p.project, p.spider, p.job)
            if self.local_items:
                s += "<td><a href='/items/%s/%s/%s.jl'>Items</a></td>" % (p.project, p.spider, p.job)
            s += "</tr>"
        s += "</table>"
        s += "</body>"
        s += "</html>"

        txrequest.setHeader('Content-Type', 'text/html; charset=utf-8')
        txrequest.setHeader('Content-Length', len(s))

        return s.encode('utf-8')
