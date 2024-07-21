import io
import pkgutil


def get_egg_data(basename):
    return pkgutil.get_data("tests", f"fixtures/{basename}.egg")


def has_settings(root):
    # https://github.com/scrapy/scrapyd/issues/526
    return root._config.cp.has_section("settings")


def root_add_version(root, project, version, basename):
    root.eggstorage.put(io.BytesIO(get_egg_data(basename)), project, version)
