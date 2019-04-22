from zope.interface import implementer

from .interfaces import ISpiderScheduler
from .utils import get_spider_queues

@implementer(ISpiderScheduler)
class SpiderScheduler(object):

    def __init__(self, config):
        self.config = config
        self.update_projects()

    def schedule(self, project, spider_name, priority=0.0, **spider_args):
        q = self.queues[project]
        # priority passed as kw for compat w/ custom queue. TODO use pos in 1.4
        q.add(spider_name, priority=priority, **spider_args)

    def list_projects(self):
        return self.queues.keys()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)
