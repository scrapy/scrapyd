import sys
import tempfile
from configparser import ConfigParser
from os import path

from twisted.application import app
from twisted.internet import reactor
from twisted.python import log

from scrapyd import Config
from scrapyd.app import application


def _get_config(http_port=None, authentication=None):
    scrapyd_config = Config()
    if http_port is None:
        http_port = 6800

    section = 'scrapyd'
    scrapyd_config.cp.set(section, 'http_port', str(http_port))

    if authentication is not None:
        username, password = authentication.split(":")
        scrapyd_config.cp.set(section, 'username', username)
        scrapyd_config.cp.set(section, 'password', password)
    return scrapyd_config


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    http_port = int(sys.argv[1])
    authentication = sys.argv[2] if len(sys.argv) == 3 else None
    conf = _get_config(http_port=http_port, authentication=authentication)
    application = application(config=conf)
    app.startApplication(application, False)
    reactor.run()
