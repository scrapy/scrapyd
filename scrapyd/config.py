import glob
import os.path
from configparser import ConfigParser, NoOptionError, NoSectionError
from pkgutil import get_data

from scrapy.utils.conf import closest_scrapy_cfg


class Config:
    """A ConfigParser wrapper to support defaults when calling instance
    methods, and also tied to a single section"""

    SECTION = "scrapyd"

    def __init__(self, values=None, extra_sources=()):
        if values is None:
            self.cp = ConfigParser()
            self.cp.read_string(get_data(__package__, "default_scrapyd.conf").decode())
            self.cp.read(
                [
                    "/etc/scrapyd/scrapyd.conf",
                    "c:\\scrapyd\\scrapyd.conf",
                    *sorted(glob.glob("/etc/scrapyd/conf.d/*")),
                    "scrapyd.conf",
                    os.path.expanduser("~/.scrapyd.conf"),
                    closest_scrapy_cfg(),
                    *extra_sources,
                ]
            )
        else:
            self.cp = ConfigParser(values)
            self.cp.add_section(self.SECTION)

    def get(self, option, default=None):
        return self._get(self.cp.get, option, default)

    def getint(self, option, default=None):
        return self._get(self.cp.getint, option, default)

    def getfloat(self, option, default=None):
        return self._get(self.cp.getfloat, option, default)

    def getboolean(self, option, default=None):
        return self._get(self.cp.getboolean, option, default)

    def _get(self, method, option, default):
        try:
            return method(self.SECTION, option)
        except (NoSectionError, NoOptionError):
            if default is not None:
                return default
            raise

    def items(self, section, default=None):
        try:
            return self.cp.items(section)
        except NoSectionError:
            if default is not None:
                return default
            raise
