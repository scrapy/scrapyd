from twisted.application.service import Application
from twisted.application.internet import TimerService, TCPServer
from twisted.web import server
from twisted.python import log

from scrapy.utils.misc import load_object

from .interfaces import IEggStorage, IPoller, ISpiderScheduler, IEnvironment

from .website import Root
from .config import Config

interfaces = [
        (IEggStorage, 'eggstorage'),
        (ISpiderScheduler, 'spider_scheduler'),
        (IEnvironment, 'environment'),
        # IPoller has to be the last interface in the list
        (IPoller, 'poller'),
]

def get_component_class(key, default_value):
    return load_object(obj_name) 

def application(config, components=interfaces):
    app = Application("Scrapyd")
    http_port = config.getint('http_port', 6800)
    bind_address = config.get('bind_address', '0.0.0.0')

    for interface, key in interfaces:
        path = config.get(key)
        cls = load_object(path)
        component = cls(config)
        app.setComponent(interface, component)
    poller = component
        
    laupath = config.get('launcher', 'scrapyd.launcher.Launcher')
    laucls = load_object(laupath) 
    launcher = laucls(config, app)

    poll_every = config.getint("poll_every", 5)
    timer = TimerService(poll_every, poller.poll)
    
    webservice = TCPServer(http_port, server.Site(Root(config, app)), interface=bind_address)
    log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
            bind_address=bind_address, http_port=http_port)

    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
