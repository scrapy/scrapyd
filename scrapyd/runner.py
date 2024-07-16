import os
import sys
from contextlib import contextmanager

from scrapy.utils.misc import load_object

from scrapyd import Config
from scrapyd.eggutils import activate_egg


@contextmanager
def project_environment(project):
    config = Config()
    eggstorage_path = config.get(
        'eggstorage', 'scrapyd.eggstorage.FilesystemEggStorage'
    )
    eggstorage_cls = load_object(eggstorage_path)
    eggstorage = eggstorage_cls(config)

    eggversion = os.environ.get('SCRAPYD_EGG_VERSION', None)
    version, eggfile = eggstorage.get(project, eggversion)
    if eggfile:
        activate_egg(eggfile.name)
        eggfile.close()

    assert 'scrapy.conf' not in sys.modules, "Scrapy settings already loaded"
    yield


def main():
    project = os.environ['SCRAPY_PROJECT']
    with project_environment(project):
        from scrapy.cmdline import execute
        execute()


if __name__ == '__main__':
    main()
