import re
from glob import glob
from os import path, makedirs, remove
from shutil import copyfileobj, rmtree
from distutils.version import LooseVersion

from zope.interface import implementer

from .interfaces import IEggStorage

@implementer(IEggStorage)
class FilesystemEggStorage(object):

    def __init__(self, config):
        self.basedir = config.get('eggs_dir', 'eggs')

    def put(self, eggfile, project, version):
        eggpath = self._eggpath(project, version)
        eggdir = path.dirname(eggpath)
        if not path.exists(eggdir):
            makedirs(eggdir)
        with open(eggpath, 'wb') as f:
            copyfileobj(eggfile, f)

    def get(self, project, version=None):
        if version is None:
            try:
                version = self.list(project)[-1]
            except IndexError:
                return None, None
        return version, open(self._eggpath(project, version), 'rb')

    def list(self, project):
        eggdir = path.join(self.basedir, project)
        versions = [path.splitext(path.basename(x))[0] \
            for x in glob("%s/*.egg" % eggdir)]
        return sorted(versions, key=LooseVersion)

    def delete(self, project, version=None):
        if version is None:
            rmtree(path.join(self.basedir, project))
        else:
            remove(self._eggpath(project, version))
            if not self.list(project): # remove project if no versions left
                self.delete(project)

    def _eggpath(self, project, version):
        sanitized_version = re.sub(r'[^a-zA-Z0-9_-]', '_', version)
        x = path.join(self.basedir, project, "%s.egg" % sanitized_version)
        return x
