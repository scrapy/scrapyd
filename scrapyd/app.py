from twisted.application.service import Application
from twisted.application.internet import TimerService, TCPServer, TCPClient
from twisted.internet.protocol import ClientCreator
from twisted.web import server
from twisted.python import log

from scrapy.utils.misc import load_object

from .interfaces import IEggStorage, IPoller, ISpiderScheduler, IEnvironment, IPubSub
from .eggstorage import FilesystemEggStorage
from .scheduler import SpiderScheduler
from .poller import QueuePoller
from .environ import Environment
from scrapyd.txredis import ScrapyRedisSubscriberFactory
from .website import Root

def application(config):
    app = Application("Scrapyd")
    http_port = config.getint('http_port', 6800)
    bind_address = config.get('bind_address', '0.0.0.0')
    poll_interval = config.getfloat('poll_interval', 5)

    poller = QueuePoller(config)
    eggstorage = FilesystemEggStorage(config)
    scheduler = SpiderScheduler(config)
    environment = Environment(config)


    #pubSubPath = config.get('pubSub', 'scrapyd.pubsub.PubSub')
    #pubSubCls = load_object(pubSubPath)
    #pubSub = pubSubCls(config, app)

    app.setComponent(IPoller, poller)
    app.setComponent(IEggStorage, eggstorage)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)
    #app.setComponent(IPubSub, pubSub)

    laupath = config.get('launcher', 'scrapyd.launcher.Launcher')
    laucls = load_object(laupath)
    launcher = laucls(config, app)

    timer = TimerService(poll_interval, poller.poll)
    webservice = TCPServer(http_port, server.Site(Root(config, app)), interface=bind_address)
    log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
            bind_address=bind_address, http_port=http_port)

    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    redisservice = TCPClient('localhost', 6379, ScrapyRedisSubscriberFactory)
    redisservice.setServiceParent(app)

    return app
