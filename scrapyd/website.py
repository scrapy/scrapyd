import socket,re

from twisted.web.template import flattenString
from datetime import datetime, timedelta
from scrapy.utils.misc import load_object
from six.moves.urllib.parse import urlparse
from twisted.web import resource, static
from twisted.application.service import IServiceCollection

from .interfaces import IPoller, IEggStorage, ISpiderScheduler


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
        self.config = config

        if logsdir:
            self.putChild(b'logs', static.File(logsdir.encode('ascii', 'ignore'), 'text/plain'))
        if local_items:
            self.putChild(b'items', static.File(itemsdir, 'text/plain'))

        services = config.items('services', ())
        for servName, servClsName in services:
          servCls = load_object(servClsName)
          self.putChild(servName.encode('utf-8'), servCls(self))

        views = config.items('views', ())
        for viewName,viewElement in views:
            route = re.search(r"(?:\/|)(.*)",viewName).group(1)
            self.putChild(str.encode(route),BaseView(self,viewElement))

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

class BaseView(resource.Resource):
    """ Base view class : resource for all app views
    has only get tmethos and renders view element that have been set in config"""

    isLeaf = True

    def __init__(self, root, viewElement):
        resource.Resource.__init__(self)
        self.view = load_object(viewElement)()
        # sets root as _root for all view elements
        setattr(self.view,"_root",root)

    def render_GET(self, txrequest):
        # rendering view , a deffered result
        txrequest.setHeader('Content-Type', 'text/html; charset=utf-8')
        response = flattenString(txrequest,self.view).result
        # reponse is deffered should get cnverted to string in order to calculate lenght 
        txrequest.setHeader('Content-Length', str(len(str(response).encode('utf8'))))
        return response
