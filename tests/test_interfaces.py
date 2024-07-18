import pytest
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from zope.interface.verify import verifyClass

from scrapyd.basicauth import PublicHTMLRealm, StringCredentialsChecker
from scrapyd.eggstorage import FilesystemEggStorage
from scrapyd.environ import Environment
from scrapyd.interfaces import IEggStorage, IEnvironment, IJobStorage, IPoller, ISpiderQueue, ISpiderScheduler
from scrapyd.jobstorage import MemoryJobStorage, SqliteJobStorage
from scrapyd.poller import QueuePoller
from scrapyd.scheduler import SpiderScheduler
from scrapyd.spiderqueue import SqliteSpiderQueue


@pytest.mark.parametrize(
    ("cls", "interface"),
    [
        (PublicHTMLRealm, IRealm),
        (StringCredentialsChecker, ICredentialsChecker),
        (FilesystemEggStorage, IEggStorage),
        (Environment, IEnvironment),
        (MemoryJobStorage, IJobStorage),
        (SqliteJobStorage, IJobStorage),
        (QueuePoller, IPoller),
        (SpiderScheduler, ISpiderScheduler),
        (SqliteSpiderQueue, ISpiderQueue),
    ],
)
def test_interface(cls, interface):
    verifyClass(interface, cls)
