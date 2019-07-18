from six import iteritems
from twisted.internet.defer import inlineCallbacks, maybeDeferred, returnValue

from scrapyd.poller import QueuePoller


class FixQueuePoller(QueuePoller):

    @inlineCallbacks
    def poll(self):
        if not self.dq.waiting:
            return
        project_with_highest_priority = None
        for p, q in iteritems(self.queues):
            project_with_highest_priority = q.get_project_with_highest_priority()
            break
        if project_with_highest_priority:
            q = self.queues[project_with_highest_priority]
            msg = yield maybeDeferred(q.pop)
            if msg is not None:  # In case of a concurrently accessed queue
                returnValue(self.dq.put(self._message(msg, project_with_highest_priority)))
