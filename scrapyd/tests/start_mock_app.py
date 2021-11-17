import argparse
import sys

from twisted.application import app
from twisted.internet import reactor
from twisted.python import log

from scrapyd import Config
from scrapyd.app import application


def _get_config(args):
    scrapyd_config = Config()
    section = 'scrapyd'
    scrapyd_config.cp.set(section, 'http_port', args.http_port)

    if args.auth is not None:
        username, password = args.auth.split(":")
        scrapyd_config.cp.set(section, 'username', username)
        scrapyd_config.cp.set(section, 'password', password)

    return scrapyd_config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('http_port', default=6800)
    parser.add_argument('--auth', default=None)
    args = parser.parse_args()
    log.startLogging(sys.stdout)
    conf = _get_config(
        args
    )
    application = application(config=conf)
    app.startApplication(application, False)
    reactor.run()
