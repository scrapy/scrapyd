from zope.interface import implementer

from scrapyd import sqlite
from scrapyd.interfaces import ISpiderQueue


@implementer(ISpiderQueue)
class SqliteSpiderQueue:
    def __init__(self, config, project, table="spider_queue"):
        self.q = sqlite.initialize(sqlite.JsonSqlitePriorityQueue, config, project, table)

    def add(self, name, priority=0.0, **spider_args):
        message = spider_args.copy()
        message["name"] = name
        self.q.put(message, priority=priority)

    def pop(self):
        return self.q.pop()

    def count(self):
        return len(self.q)

    def list(self):
        return [message for message, _ in self.q]

    def remove(self, func):
        return self.q.remove(func)

    def clear(self):
        self.q.clear()
