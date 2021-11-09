import sys
import tempfile

from twisted.application import app
from twisted.internet import reactor
from twisted.python import log

from scrapyd import get_application, Config


def _get_config(http_port=None, authentication=None):
    if http_port is None:
        http_port = "6800"
    scrapyd_conf = f"""
[scrapyd]
http_port = {str(http_port)}
    """
    if authentication is not None:
        username, password = authentication.split(":")
        scrapyd_conf += "\n"
        scrapyd_conf += "username = " + username + "\n"
        scrapyd_conf += "password = " + password + "\n"
    tmp_file = tempfile.NamedTemporaryFile()
    tmp_file.write(scrapyd_conf.encode())
    tmp_file.seek(0)
    return Config(extra_sources=[tmp_file.name])


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    http_port = int(sys.argv[1])
    authentication = sys.argv[2] if len(sys.argv) == 3 else None
    conf = _get_config(http_port=http_port, authentication=authentication)
    application = get_application(config=conf)
    app.startApplication(application, False)
    reactor.run()
