from zope.interface import implementer

from scrapyd.interfaces import ISpiderQueue
from scrapyd.sqlite import JsonSqlitePriorityQueue


@implementer(ISpiderQueue)
class SqliteSpiderQueue(object):

    def __init__(self, database=None, table='spider_queue'):
        self.q = JsonSqlitePriorityQueue(database, table)

    def add(self, name, priority=0.0, **spider_args):
        d = spider_args.copy()
        d['name'] = name
        self.q.put(d, priority=priority)

    def pop(self):
        return self.q.pop()

    def count(self):
        return len(self.q)

    def list(self):
        return [x[0] for x in self.q]

    def remove(self, func):
        return self.q.remove(func)

    def clear(self):
        self.q.clear()

    def get_project_with_highest_priority(self):
        if self.q.project_priority_map:
            return sorted(self.q.project_priority_map,
                          key=lambda x: self.q.project_priority_map[x], reverse=True)[0]
        else:
            return None
