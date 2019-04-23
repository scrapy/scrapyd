import os

from twisted.application.service import Application
from twisted.application.internet import TimerService, TCPServer, UNIXServer
from twisted.web import server
from twisted.python import log

from scrapy.utils.misc import load_object

from .interfaces import IEggStorage, IPoller, ISpiderScheduler, IEnvironment
from .eggstorage import FilesystemEggStorage
from .scheduler import SpiderScheduler
from .poller import QueuePoller
from .environ import Environment
from .config import Config

def application(config):
    app = Application("Scrapyd")
    http_port = config.getint('http_port', 6800)
    bind_address = config.get('bind_address', '127.0.0.1')
    uds_path = config.get('unix_socket_path', '')
    uds_path = uds_path and os.path.abspath(uds_path)

    poll_interval = config.getfloat('poll_interval', 5)

    poller = QueuePoller(config)
    eggstorage = FilesystemEggStorage(config)
    scheduler = SpiderScheduler(config)
    environment = Environment(config)

    app.setComponent(IPoller, poller)
    app.setComponent(IEggStorage, eggstorage)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)

    laupath = config.get('launcher', 'scrapyd.launcher.Launcher')
    laucls = load_object(laupath)
    launcher = laucls(config, app)

    webpath = config.get('webroot', 'scrapyd.website.Root')
    website = server.Site(load_object(webpath)(config, app))

    timer = TimerService(poll_interval, poller.poll)

    launcher.setServiceParent(app)
    timer.setServiceParent(app)

    if http_port:
        webservice = TCPServer(http_port, website, interface=bind_address)
        log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
                http_port=http_port, bind_address=bind_address)
        webservice.setServiceParent(app)
    if uds_path:
        webservice = UNIXServer(uds_path, website, mode=0o660)
        log.msg(format=u"Scrapyd web console available at http+unix://%(uds_path)s",
                uds_path=uds_path)
        webservice.setServiceParent(app)

    return app
