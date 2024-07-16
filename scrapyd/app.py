import os
import sys

from scrapy.utils.misc import load_object
from twisted.application.internet import TCPServer, TimerService, UNIXServer
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
    bind_address = os.getenv('SCRAPYD_BIND_ADDRESS') or config.get('bind_address', '127.0.0.1')
    http_port = int(os.getenv('SCRAPYD_HTTP_PORT') or config.getint('http_port', 6800))
    unix_socket_path = os.getenv('SCRAPYD_UNIX_SOCKET_PATH') or config.get('unix_socket_path', '')

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
    resource = server.Site(create_wrapped_resource(webroot_cls, config, app))

    if bind_address and http_port:
        webservice = TCPServer(http_port, resource, interface=bind_address)
        log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
                bind_address=bind_address, http_port=http_port)
    if unix_socket_path:
        unix_socket_path = os.path.abspath(unix_socket_path)
        webservice = UNIXServer(unix_socket_path, resource, mode=0o660)
        log.msg(format="Scrapyd web console available at http+unix://%(unix_socket_path)s",
                unix_socket_path=unix_socket_path)

    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
