import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

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

    # setdefault() was added in https://github.com/scrapy/scrapyd/commit/0641a57. It's not clear why, since the egg
    # should control its settings module. That said, it is unlikely to already be set.
    os.environ.setdefault("SCRAPY_SETTINGS_MODULE", distribution.get_entry_info("scrapy", "settings").module_name)


@contextmanager
def project_environment(project):
    config = Config()
    eggstorage = initialize_component(config, "eggstorage", "scrapyd.eggstorage.FilesystemEggStorage")

    eggversion = os.environ.get("SCRAPYD_EGG_VERSION", None)
    sanitized_version, egg = eggstorage.get(project, eggversion)

    tmp = None
    # egg can be None if the project is not in egg storage: for example, if Scrapyd is invoked within a Scrapy project.
    if egg:
        try:
            if hasattr(egg, "name"):  # for example, FileIO
                activate_egg(egg.name)
            else:  # for example, BytesIO
                prefix = f"{project}-{sanitized_version}-"
                with tempfile.NamedTemporaryFile(suffix=".egg", prefix=prefix, delete=False) as tmp:
                    shutil.copyfileobj(egg, tmp)
                activate_egg(tmp.name)
        finally:
            egg.close()

    try:
        yield
    finally:
        if tmp:
            Path(tmp.name).unlink()


def main():
    project = os.environ["SCRAPY_PROJECT"]
    with project_environment(project):
        from scrapy.cmdline import execute  # noqa: PLC0415

        # This calls scrapy.utils.project.get_project_settings(). It uses SCRAPY_SETTINGS_MODULE if set. Otherwise, it
        # calls scrapy.utils.conf.init_env(), which reads Scrapy's configuration sources, looks for a project matching
        # SCRAPY_PROJECT in the [settings] section, and uses its value for SCRAPY_SETTINGS_MODULE.
        # https://docs.scrapy.org/en/latest/topics/commands.html#configuration-settings
        execute()


if __name__ == "__main__":
    main()
