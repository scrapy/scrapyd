from zope.interface import implementer
from six import iteritems
from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred, returnValue

from .utils import get_spider_queues
from .interfaces import IPoller

@implementer(IPoller)
class QueuePoller(object):

    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue()
        # For backward compatibility with custom SqliteSpiderQueue and JsonSqlitePriorityQueue
        # TODO: remove it and add method get_project_with_highest_priority in ISpiderQueue in 1.4
        self.support_comparing_priorities = None

    @inlineCallbacks
    def poll(self):
        if not self.dq.waiting:
            return

        if self.support_comparing_priorities is None:
            self.test_comparing_priorities()

        project_with_highest_priority = None
        if self.support_comparing_priorities:
            for p, q in iteritems(self.queues):
                project_with_highest_priority = q.get_project_with_highest_priority()
                break
            if project_with_highest_priority:
                q = self.queues[project_with_highest_priority]
                msg = yield maybeDeferred(q.pop)
                if msg is not None:  # In case of a concurrently accessed queue
                    returnValue(self.dq.put(self._message(msg, project_with_highest_priority)))
        if not self.support_comparing_priorities or not project_with_highest_priority:
            for p, q in iteritems(self.queues):
                c = yield maybeDeferred(q.count)
                if c:
                    msg = yield maybeDeferred(q.pop)
                    if msg is not None:  # In case of a concurrently accessed queue
                        returnValue(self.dq.put(self._message(msg, p)))

    def next(self):
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)

    def _message(self, queue_msg, project):
        d = queue_msg.copy()
        d['_project'] = project
        d['_spider'] = d.pop('name')
        return d

    def test_comparing_priorities(self):
        for p, q in iteritems(self.queues):
            try:
                getattr(q, 'get_project_with_highest_priority')
                getattr(q.q, 'project_priority_map')
            except AttributeError:
                self.support_comparing_priorities = False
            else:
                self.support_comparing_priorities = True
            return
