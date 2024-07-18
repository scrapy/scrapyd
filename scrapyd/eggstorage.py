import os
import re
import shutil
from glob import escape, glob

from zope.interface import implementer

from scrapyd.exceptions import DirectoryTraversalError
from scrapyd.interfaces import IEggStorage
from scrapyd.utils import sorted_versions


@implementer(IEggStorage)
class FilesystemEggStorage(object):

    def __init__(self, config):
        self.basedir = config.get('eggs_dir', 'eggs')

    def put(self, eggfile, project, version):
        path = self._egg_path(project, version)

        directory = os.path.dirname(path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        with open(path, 'wb') as f:
            shutil.copyfileobj(eggfile, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        return version, open(self._egg_path(project, version), 'rb')

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
            shutil.rmtree(self._get_path(project))
        else:
            os.remove(self._egg_path(project, version))
            if not self.list(project):  # remove project if no versions left
                self.delete(project)

    def _egg_path(self, project, version):
        sanitized_version = re.sub(r'[^A-Za-z0-9_-]', '_', version)
        return self._get_path(project, f"{sanitized_version}.egg")

    def _get_path(self, project, *trusted):
        resolvedir = os.path.realpath(self.basedir)
        projectdir = os.path.realpath(os.path.join(resolvedir, project))

        if os.path.commonprefix((projectdir, resolvedir)) != resolvedir:
            raise DirectoryTraversalError(project)

        return os.path.join(projectdir, *trusted)
