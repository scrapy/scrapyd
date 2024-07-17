import os
import re
import shutil
from glob import glob

from zope.interface import implementer

from scrapyd.interfaces import IEggStorage
from scrapyd.utils import sorted_versions


@implementer(IEggStorage)
class FilesystemEggStorage(object):

    def __init__(self, config):
        self.basedir = config.get('eggs_dir', 'eggs')

    def put(self, eggfile, project, version):
        eggpath = self._eggpath(project, version)
        eggdir = os.path.dirname(eggpath)
        if not os.path.exists(eggdir):
            os.makedirs(eggdir)
        with open(eggpath, 'wb') as f:
            shutil.copyfileobj(eggfile, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        return version, open(self._eggpath(project, version), 'rb')

    def list(self, project):
        versions = [
            os.path.splitext(os.path.basename(path))[0]
            for path in glob(os.path.join(self.basedir, project, "*.egg"))
        ]
        return sorted_versions(versions)

    def list_projects(self):
        if os.path.exists(self.basedir):
            return [name for name in os.listdir(self.basedir) if os.path.isdir(os.path.join(self.basedir, name))]
        return []

    def delete(self, project, version=None):
        if version is None:
            shutil.rmtree(os.path.join(self.basedir, project))
        else:
            os.remove(self._eggpath(project, version))
            if not self.list(project):  # remove project if no versions left
                self.delete(project)

    def _eggpath(self, project, version):
        sanitized_version = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        return os.path.join(self.basedir, project, f"{sanitized_version}.egg")
