import os

from twisted.application.internet import TCPServer, TimerService, UNIXServer
from twisted.application.service import Application
from twisted.logger import Logger
from twisted.web import server

from scrapyd.basicauth import wrap_resource
from scrapyd.environ import Environment
from scrapyd.interfaces import IEggStorage, IEnvironment, IJobStorage, IPoller, ISpiderScheduler
from scrapyd.scheduler import SpiderScheduler
from scrapyd.utils import initialize_component

log = Logger()


def application(config):
    app = Application("Scrapyd")
    bind_address = os.getenv("SCRAPYD_BIND_ADDRESS") or config.get("bind_address", "127.0.0.1")
    http_port = int(os.getenv("SCRAPYD_HTTP_PORT") or config.getint("http_port", "6800"))
    unix_socket_path = os.getenv("SCRAPYD_UNIX_SOCKET_PATH") or config.get("unix_socket_path", "")
    poll_interval = config.getfloat("poll_interval", 5)

    environment = Environment(config)
    scheduler = SpiderScheduler(config)
    poller = initialize_component(config, "poller", "scrapyd.poller.QueuePoller")
    jobstorage = initialize_component(config, "jobstorage", "scrapyd.jobstorage.MemoryJobStorage")
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")

    app.setComponent(IEnvironment, environment)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IPoller, poller)
    app.setComponent(IJobStorage, jobstorage)
    app.setComponent(IEggStorage, eggstorage)

    # launcher uses jobstorage in initializer, and uses poller and environment.
    launcher = initialize_component(config, "launcher", "scrapyd.launcher.Launcher", app)

    timer = TimerService(poll_interval, poller.poll)

    # webroot uses launcher, poller, scheduler and environment.
    webroot = initialize_component(config, "webroot", "scrapyd.website.Root", app)
    resource = server.Site(wrap_resource(webroot, config))
    if bind_address and http_port:
        webservice = TCPServer(http_port, resource, interface=bind_address)
        log.info(
            "Scrapyd web console available at http://{bind_address}:{http_port}/",
            bind_address=bind_address,
            http_port=http_port,
        )
    if unix_socket_path:
        unix_socket_path = os.path.abspath(unix_socket_path)
        webservice = UNIXServer(unix_socket_path, resource, mode=0o660)
        log.info(
            "Scrapyd web console available at http+unix://{unix_socket_path}",
            unix_socket_path=unix_socket_path,
        )

    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
