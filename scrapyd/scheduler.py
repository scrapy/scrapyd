from zope.interface import implements

from .interfaces import ISpiderScheduler
from .utils import get_spider_queues
from .schedulepersist import MysqlSchedulePersist

class SpiderScheduler(object):

    implements(ISpiderScheduler)

    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.schedulePersist = MysqlSchedulePersist(config)

    def schedule(self, project, spider_name, **spider_args):
        q = self.queues[project]
        q.add(spider_name, **spider_args)
        if self.config.get('enable_postgres_persist', 'false').lower() == 'true':
            self.schedulePersist.add(project, spider_name, **spider_args)

    def list_projects(self):
        return self.queues.keys()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)
