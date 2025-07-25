import re
import shutil
from glob import escape
from pathlib import Path

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

        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("wb") as f:
            shutil.copyfileobj(eggfile, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        try:
            return version, self._egg_path(project, version).open("rb")
        except FileNotFoundError:
            return None, None

    def list(self, project):
        return sorted_versions([path.stem for path in self._get_path(escape(project)).glob("*.egg")])

    def list_projects(self):
        basedir_path = Path(self.basedir)
        if basedir_path.exists():
            return [path.name for path in basedir_path.iterdir() if path.is_dir()]
        return []

    def delete(self, project, version=None):
        if version is None:
            try:
                shutil.rmtree(self._get_path(project))
            except FileNotFoundError as e:
                raise ProjectNotFoundError from e
        else:
            try:
                self._egg_path(project, version).unlink()
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

        return Path(file.path) / Path(*trusted)
