import os
import re
import shutil
from glob import escape, glob

from packaging.version import InvalidVersion, Version
from twisted.python import filepath
from zope.interface import implementer

from scrapyd.exceptions import DirectoryTraversalError, EggNotFoundError, ProjectNotFoundError
from scrapyd.interfaces import IEggStorage


def sorted_versions(versions):
    try:
        return sorted(versions, key=Version)
    except InvalidVersion:
        return sorted(versions)


@implementer(IEggStorage)
class FilesystemEggStorage:
    def __init__(self, config):
        self.basedir = config.get("eggs_dir", "eggs")

    def put(self, eggfile, project, version):
        path = self._egg_path(project, version)

        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(path, "wb") as f:
            shutil.copyfileobj(eggfile, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        try:
            return version, open(self._egg_path(project, version), "rb")  # noqa: SIM115
        except FileNotFoundError:
            return None, None

    def list(self, project):
        return sorted_versions(
            [os.path.splitext(os.path.basename(path))[0] for path in glob(self._get_path(escape(project), "*.egg"))]
        )

    def list_projects(self):
        if os.path.exists(self.basedir):
            return [name for name in os.listdir(self.basedir) if os.path.isdir(os.path.join(self.basedir, name))]
        return []

    def delete(self, project, version=None):
        if version is None:
            try:
                shutil.rmtree(self._get_path(project))
            except FileNotFoundError as e:
                raise ProjectNotFoundError from e
        else:
            try:
                os.remove(self._egg_path(project, version))
                if not self.list(project):  # remove project if no versions left
                    self.delete(project)
            except FileNotFoundError as e:
                raise EggNotFoundError from e

    def _egg_path(self, project, version):
        sanitized_version = re.sub(r"[^A-Za-z0-9_-]", "_", version)
        return self._get_path(project, f"{sanitized_version}.egg")

    def _get_path(self, project, *trusted):
        try:
            file = filepath.FilePath(self.basedir).child(project)
        except filepath.InsecurePath as e:
            raise DirectoryTraversalError(project) from e

        return os.path.join(file.path, *trusted)
