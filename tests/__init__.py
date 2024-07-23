import io
import os.path
import pkgutil


def get_egg_data(basename):
    return pkgutil.get_data("tests", f"fixtures/{basename}.egg")


def has_settings():
    return os.path.exists("scrapy.cfg")


def root_add_version(root, project, version, basename):
    root.eggstorage.put(io.BytesIO(get_egg_data(basename)), project, version)
