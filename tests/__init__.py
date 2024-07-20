import io
import os.path
import pkgutil
import shutil


def get_egg_data(basename):
    return pkgutil.get_data("tests", f"fixtures/{basename}.egg")


def root_add_version(root, project, version, basename):
    root.eggstorage.put(io.BytesIO(get_egg_data(basename)), project, version)


def clean(config, setting):
    directory = os.path.realpath(config.get(setting))
    basedir = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
    # Avoid accidentally deleting directories outside the project.
    assert os.path.commonprefix((directory, basedir)) == basedir
    if os.path.exists(directory):
        shutil.rmtree(directory)
