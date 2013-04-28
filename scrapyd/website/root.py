from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from scrapy.utils.misc import load_object
from scrapyd.interfaces import IPoller, IEggStorage, ISpiderScheduler

class Root(resource.Resource):

    def __init__(self, config, app):
        resource.Resource.__init__(self)

        self.app = app
        self.config = config

        self.debug = config.getboolean('debug', False)
        self.runner = config.get('runner')

        self.resources = config.items('resources', ())
        for path, resource_class_name in self.resources:
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

