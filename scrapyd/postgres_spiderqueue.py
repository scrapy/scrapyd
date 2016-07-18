from zope.interface import implements

from scrapyd.interfaces import ISpiderQueue
from scrapyd.postgres import JsonPostgresPriorityQueue
#from twisted.python import log


class PostgresSpiderQueue(object):

    implements(ISpiderQueue)

    def __init__(self, database=None, table='spider_queue', project=None):
        self.q = JsonPostgresPriorityQueue(database, table, project)

    def add(self, name, **spider_args):
        d = spider_args.copy()
        d['name'] = name
        priority = float(d.pop('priority', 0))
        self.q.put(d, priority)

    def pop(self):
        return self.q.pop()

    def count(self):
        #log.msg(self.q)
        return len(self.q)

    def list(self):
        return [x[0] for x in self.q]

    def remove(self, func):
        return self.q.remove(func)

    def clear(self):
        self.q.clear()
