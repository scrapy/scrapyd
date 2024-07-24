from twisted.internet.defer import DeferredQueue, inlineCallbacks, maybeDeferred
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
            while (yield maybeDeferred(queue.count)):
                # If the "waiting" backlog is empty (that is, if the maximum number of Scrapy processes are running):
                if not self.dq.waiting:
                    return
                message = (yield maybeDeferred(queue.pop)).copy()
                # The message can be None if, for example, two Scrapyd instances share a spider queue database.
                if message is not None:
                    message["_project"] = project
                    message["_spider"] = message.pop("name")
                    # Pop a dummy item from the "waiting" backlog. and fire the message's callbacks.
                    self.dq.put(message)

    def next(self):
        """
        Add a dummy item to the "waiting" backlog (based on Twisted's implementation of DeferredQueue).
        """
        return self.dq.get()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)
