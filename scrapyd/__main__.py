import sys
from os.path import dirname, join

from twisted.scripts import twistd

import scrapyd


class ServerOptions(twistd.ServerOptions):
    synopsis = "Usage: scrapyd [options]"
    longdesc = "Scrapyd is an application for deploying and running Scrapy spiders."

    def __init__(self):
        super().__init__()
        # main() always sets -n (--nodaemon) and -y (--python=). -y can be set only once. -n is okay to leave as a
        # no-op. Scrapyd's *_dir settings don't respect --rundir.
        self.longOpt = [opt for opt in self.longOpt if opt not in ("python=", "rundir=")]

    @property
    def subCommands(self):
        return []  # remove alternatives to running txapp.py

    def getUsage(self, width=None):
        return super().getUsage(width=width)[:-11]  # remove "\nCommands:\n"


def main():
    if len(sys.argv) > 1 and "-v" in sys.argv[1:] or "--version" in sys.argv[1:]:
        print(f"Scrapyd {scrapyd.__version__}")
    else:
        sys.argv[1:1] = ["-n", "-y", join(dirname(scrapyd.__file__), "txapp.py")]
        twistd.app.run(twistd.runApp, ServerOptions)


if __name__ == "__main__":
    main()
