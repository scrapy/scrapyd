import os
import sys

from scrapy.utils.misc import load_object
from twisted.application.internet import TCPServer, TimerService
from twisted.application.service import Application
from twisted.cred.portal import Portal
from twisted.python import log
from twisted.web import server
from twisted.web.guard import BasicCredentialFactory, HTTPAuthSessionWrapper

from scrapyd.basicauth import PublicHTMLRealm, StringCredentialsChecker
from scrapyd.environ import Environment
from scrapyd.interfaces import IEggStorage, IEnvironment, IJobStorage, IPoller, ISpiderScheduler
from scrapyd.poller import QueuePoller
from scrapyd.scheduler import SpiderScheduler


def create_wrapped_resource(webroot_cls, config, app):
    username = os.getenv('SCRAPYD_USERNAME') or config.get('username', '')
    password = os.getenv('SCRAPYD_PASSWORD') or config.get('password', '')
    if ':' in username:
        sys.exit("The `username` option contains illegal character ':', "
                 "check and update the configuration file of Scrapyd")
    resource = webroot_cls(config, app)
    if username and password:
        log.msg("Basic authentication enabled")
        portal = Portal(PublicHTMLRealm(resource),
                        [StringCredentialsChecker(username, password)])
        credential_factory = BasicCredentialFactory("Auth")
        return HTTPAuthSessionWrapper(portal, [credential_factory])
    else:
        log.msg("Basic authentication disabled as either `username` or `password` is unset")
        return resource


def application(config):
    app = Application("Scrapyd")
    http_port = int(os.getenv('SCRAPYD_HTTP_PORT') or config.getint('http_port', 6800))
    bind_address = os.getenv('SCRAPYD_BIND_ADDRESS') or config.get('bind_address', '127.0.0.1')
    poll_interval = config.getfloat('poll_interval', 5)

    poller = QueuePoller(config)
    scheduler = SpiderScheduler(config)
    environment = Environment(config)

    app.setComponent(IPoller, poller)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)

    jobstorage_path = config.get('jobstorage', 'scrapyd.jobstorage.MemoryJobStorage')
    jobstorage_cls = load_object(jobstorage_path)
    jobstorage = jobstorage_cls(config)
    app.setComponent(IJobStorage, jobstorage)

    eggstorage_path = config.get('eggstorage', 'scrapyd.eggstorage.FilesystemEggStorage')
    eggstorage_cls = load_object(eggstorage_path)
    eggstorage = eggstorage_cls(config)
    app.setComponent(IEggStorage, eggstorage)

    launcher_path = config.get('launcher', 'scrapyd.launcher.Launcher')
    launcher_cls = load_object(launcher_path)
    launcher = launcher_cls(config, app)

    timer = TimerService(poll_interval, poller.poll)

    webroot_path = config.get('webroot', 'scrapyd.website.Root')
    webroot_cls = load_object(webroot_path)
    resource = create_wrapped_resource(webroot_cls, config, app)
    webservice = TCPServer(http_port, server.Site(resource), interface=bind_address)

    log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
            bind_address=bind_address, http_port=http_port)

    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
