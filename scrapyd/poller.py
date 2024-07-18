from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred, returnValue
from zope.interface import implementer

from scrapyd.interfaces import IPoller
from scrapyd.utils import get_spider_queues


@implementer(IPoller)
class QueuePoller:
    def __init__(self, config):
        self.config = config
        self.update_projects()
        self.dq = DeferredQueue()

    @inlineCallbacks
    def poll(self):
        for project, queue in self.queues.items():
            # If the "waiting" backlog is empty (that is, if the maximum number of Scrapy processes are running):
            if not self.dq.waiting:
                return
            count = yield maybeDeferred(queue.count)
            if count:
                message = yield maybeDeferred(queue.pop)
                # The message can be None if, for example, two Scrapyd instances share a spider queue database.
                if message is not None:
                    # Pop a dummy item from the "waiting" backlog. and fire the message.
                    returnValue(self.dq.put(self._message(message, project)))

    def next(self):
        """
        Add a dummy item to the "waiting" backlog (based on Twisted's implementation of DeferredQueue).
        """
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)

    def _message(self, message, project):
        new = message.copy()
        new["_project"] = project
        new["_spider"] = new.pop("name")
        return new
