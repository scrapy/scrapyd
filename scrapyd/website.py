from datetime import datetime

from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object
from jinja2 import FileSystemLoader, Environment

from .interfaces import IPoller, IEggStorage, ISpiderScheduler


class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)
        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')
        logsdir = config.get('logs_dir')
        itemsdir = config.get('items_dir')
        self.app = app
        self.putChild('', Home(self))
        if logsdir:
            self.putChild('logs', static.File(logsdir, 'text/plain'))
        if itemsdir:
            self.putChild('items', static.File(itemsdir, 'text/plain'))
        self.putChild('jobs', Jobs(self))
        self.putChild('static', static.File('static'))              # adding UI support
        services = config.items('services', ())
        for servName, servClsName in services:
            servCls = load_object(servClsName)
            self.putChild(servName, servCls(self))
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

    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render_GET(self, txrequest):
        template_loader = FileSystemLoader(searchpath=".")
        template_env = Environment(loader=template_loader)

        template_file = "templates/home.jinja"
        template = template_env.get_template(template_file)
        template_vars = {
            'projects': ', '.join(self.root.scheduler.list_projects()),
        }

        return template.render(template_vars).encode('ascii', 'ignore')


class Jobs(resource.Resource):

    def __init__(self, root):
        resource.Resource.__init__(self)
        self.root = root

    def render(self, txrequest):
        template_loader = FileSystemLoader(searchpath=".")
        template_env = Environment(loader=template_loader)

        template_file = "templates/jobs.jinja"
        template = template_env.get_template(template_file)
        template_vars = {
            'queues_items': self.root.poller.queues.items(),
            'processes_values': self.root.launcher.processes.values(),
            'launcher_finished': self.root.launcher.finished,
        }

        return template.render(template_vars).encode('ascii', 'ignore')
