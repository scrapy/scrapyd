from zope.interface import implements
from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred, returnValue
from random import sample

from .utils import get_spider_queues
from .interfaces import IPoller

class QueuePoller(object):

    implements(IPoller)

    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue(size=1)
        self.max_jobs_per_project = self.config.getint('max_jobs_per_project', 4)

    @inlineCallbacks
    def poll(self, launcher):
        if self.dq.pending:
            return
        for p, q in sample(self.queues.items(), len(self.queues)):
            c = yield maybeDeferred(q.count)
            if c and self._has_slot_for_project(p, launcher):
                msg = yield maybeDeferred(q.pop)
                returnValue(self.dq.put(self._message(msg, p)))

    def _has_slot_for_project(self, project_name, launcher):
        running_jobs = 0
        spiders = launcher.processes.values()
        
        
        for s in spiders:
            if s.project == project_name:
                running_jobs += 1
        return running_jobs < self.max_jobs_per_project

    def next(self):
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)

    def _message(self, queue_msg, project):
        d = queue_msg.copy()
        d['_project'] = project
        d['_spider'] = d.pop('name')
        return d
