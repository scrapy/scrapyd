import os
import shutil
import tempfile
from contextlib import contextmanager

from scrapy.utils.misc import load_object

from scrapyd import Config
from scrapyd.eggutils import activate_egg


@contextmanager
def project_environment(project):
    config = Config()
    eggstorage_path = config.get("eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")
    eggstorage_cls = load_object(eggstorage_path)
    eggstorage = eggstorage_cls(config)

    eggversion = os.environ.get("SCRAPYD_EGG_VERSION", None)
    version, egg = eggstorage.get(project, eggversion)

    tmp = None
    if egg:
        try:
            if hasattr(egg, "name"):  # for example, FileIO
                activate_egg(egg.name)
            else:  # for example, BytesIO
                tmp = tempfile.NamedTemporaryFile(suffix=".egg", prefix=f"{project}-{version}-", delete=False)
                shutil.copyfileobj(egg, tmp)
                tmp.close()
                activate_egg(tmp.name)
        finally:
            egg.close()

    try:
        yield
    finally:
        if tmp:
            os.remove(tmp.name)


def main():
    project = os.environ["SCRAPY_PROJECT"]
    with project_environment(project):
        from scrapy.cmdline import execute

        execute()


if __name__ == "__main__":
    main()
