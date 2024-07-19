import os
import shutil
import tempfile
from contextlib import contextmanager

import pkg_resources

from scrapyd import Config
from scrapyd.exceptions import BadEggError
from scrapyd.utils import initialize_component


def activate_egg(eggpath):
    """Activate a Scrapy egg file. This is meant to be used from egg runners
    to activate a Scrapy egg file. Don't use it from other code as it may
    leave unwanted side effects.
    """
    distributions = pkg_resources.find_distributions(eggpath)
    if isinstance(distributions, tuple):
        raise BadEggError

    try:
        distribution = next(distributions)
    except StopIteration:
        raise BadEggError from None

    distribution.activate()

    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", distribution.get_entry_info("scrapy", "settings").module_name)


@contextmanager
def project_environment(project):
    config = Config()
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")

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
