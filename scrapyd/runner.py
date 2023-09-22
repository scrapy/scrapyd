import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

from scrapy.utils.misc import load_object

from scrapyd import Config
from scrapyd.eggutils import activate_egg


@contextmanager
def project_environment(project):
    eggversion = os.environ.get('SCRAPYD_EGG_VERSION', None)
    config = Config()
    eggstorage_path = config.get(
        'eggstorage', 'scrapyd.eggstorage.FilesystemEggStorage'
    )
    eggstorage_cls = load_object(eggstorage_path)
    eggstorage = eggstorage_cls(config)

    version, eggfile = eggstorage.get(project, eggversion)
    if eggfile:
        prefix = '%s-%s-' % (project, version)
        f = tempfile.NamedTemporaryFile(suffix='.egg', prefix=prefix, delete=False)
        shutil.copyfileobj(eggfile, f)
        f.close()
        activate_egg(f.name)
    else:
        f = None
    try:
        assert 'scrapy.conf' not in sys.modules, "Scrapy settings already loaded"
        yield
    finally:
        if f:
            os.remove(f.name)


def main():
    project = os.environ['SCRAPY_PROJECT']
    with project_environment(project):
        from scrapy.cmdline import execute
        execute()


if __name__ == '__main__':
    main()
