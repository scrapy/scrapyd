import glob
import os.path
from configparser import ConfigParser, NoOptionError, NoSectionError
from contextlib import suppress
from pkgutil import get_data

from scrapy.utils.conf import closest_scrapy_cfg


class Config:
    """A ConfigParser wrapper to support defaults when calling instance
    methods, and also tied to a single section"""

    SECTION = "scrapyd"

    def __init__(self, values=None, extra_sources=()):
        if values is None:
            self.cp = ConfigParser()
            self.cp.read_string(get_data(__package__, "default_scrapyd.conf").decode("utf8"))
            for source in self._get_sources(extra_sources):
                with suppress(OSError), open(source) as f:
                    self.cp.read_file(f)
        else:
            self.cp = ConfigParser(values)
            self.cp.add_section(self.SECTION)

    def _get_sources(self, extra_sources):
        sources = [
            "c:\\scrapyd\\scrapyd.conf",
            "/etc/scrapyd/scrapyd.conf",
            *sorted(glob.glob("/etc/scrapyd/conf.d/*")),
            "scrapyd.conf",
            os.path.expanduser("~/.scrapyd.conf"),
        ]
        if scrapy_cfg := closest_scrapy_cfg():
            sources.append(scrapy_cfg)
        sources.extend(extra_sources)
        return sources

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
