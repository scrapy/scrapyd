from zope.interface import implements
from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred, returnValue

from .utils import get_spider_queues
from .interfaces import IPoller
from twisted.application.service import IServiceCollection


class QueuePoller(object):

    implements(IPoller)

    def __init__(self, config, app):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue(size=1)
        self.max_jobs_per_project = self.config.get('max_jobs_per_project', 4)
        self.app = app

    @inlineCallbacks
    def poll(self):
        if self.dq.pending:
            return
        for p, q in self.queues.iteritems():
            c = yield maybeDeferred(q.count)
            if c and self.has_slot_for_project(p):
                  msg = yield maybeDeferred(q.pop)
                  returnValue(self.dq.put(self._message(msg, p)))

    def has_slot_for_project(self, project_name):
        running_jobs = 0
        spiders = self.launcher.processes.values()
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

    @property
    def launcher(self):
        """
        Copied from website.Root
        Should do some refactory to avoid this duplicated code
        """
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed('launcher')
