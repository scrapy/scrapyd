from twisted.application.service import Application
from twisted.application.internet import TimerService, TCPServer
from twisted.web import server
from twisted.python import log

from scrapy.utils.misc import load_object

from scrapyd.interfaces import IEggStorage, IPoller, ISpiderScheduler, IEnvironment, IPubSub
from scrapyd.eggstorage import FilesystemEggStorage
from scrapyd.poller import QueuePoller
from scrapyd.environ import Environment
from scrapyd.website import Root

def application(config):
    app = Application("Scrapyd")
    http_port = config.getint('http_port', 6800)
    bind_address = config.get('bind_address', '0.0.0.0')
    poll_interval = config.getfloat('poll_interval', 5)

    poller = QueuePoller(config)
    eggstorage = FilesystemEggStorage(config)

    schedpath = config.get('scheduler', 'scrapyd.scheduler.SpiderScheduler')
    schedCls = load_object(schedpath)
    scheduler = schedCls(config, app)

    environment = Environment(config)

    pubsub_path = config.get('pubsub', 'scrapyd.pubsub.BasePubSub')
    pubsubCls = load_object(pubsub_path)
    pubsub = pubsubCls(config, app)

    app.setComponent(IPoller, poller)
    app.setComponent(IEggStorage, eggstorage)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)
    app.setComponent(IPubSub, pubsub)

    laupath = config.get('launcher', 'scrapyd.launcher.Launcher')
    laucls = load_object(laupath)
    launcher = laucls(config, app)

    timer = TimerService(poll_interval, poller.poll)
    webservice = TCPServer(http_port, server.Site(Root(config, app)), interface=bind_address)
    log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
            bind_address=bind_address, http_port=http_port)

    pubsub.setServiceParent(app)
    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)
    return app
