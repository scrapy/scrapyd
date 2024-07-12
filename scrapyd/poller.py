from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred, returnValue
from zope.interface import implementer

from scrapyd.interfaces import IPoller
from scrapyd.utils import get_spider_queues


@implementer(IPoller)
class QueuePoller(object):

    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue()

    @inlineCallbacks
    def poll(self):
        if not self.dq.waiting:
            return
        for project, queue in self.queues.items():
            count = yield maybeDeferred(queue.count)
            if count:
                message = yield maybeDeferred(queue.pop)
                if message is not None:  # In case of a concurrently accessed queue
                    returnValue(self.dq.put(self._message(message, project)))

    def next(self):
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)

    def _message(self, message, project):
        new = message.copy()
        new['_project'] = project
        new['_spider'] = new.pop('name')
        return new
