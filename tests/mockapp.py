import argparse
import sys

from twisted.application import app
from twisted.internet import reactor
from twisted.python import log

from scrapyd import Config
from scrapyd.app import application

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("http_port")
    parser.add_argument("--username")
    parser.add_argument("--password")
    args = parser.parse_args()

    config = Config()
    config.cp.set(Config.SECTION, "http_port", args.http_port)
    if args.username and args.password:
        config.cp.set(Config.SECTION, "username", args.username)
        config.cp.set(Config.SECTION, "password", args.password)

    log.startLogging(sys.stdout)

    app.startApplication(application(config=config), save=False)

    reactor.run()
