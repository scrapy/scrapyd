from scrapyd.spiderqueue import SqliteSpiderQueue
from scrapyd.contrib.fix_poll_order.sqlite import FixJsonSqlitePriorityQueue


class FixSqliteSpiderQueue(SqliteSpiderQueue):

    def __init__(self, database=None, table='spider_queue_with_triggers'):
        self.q = FixJsonSqlitePriorityQueue(database, table)

    def get_project_with_highest_priority(self):
        if self.q.project_priority_map:
            return sorted(self.q.project_priority_map,
                          key=lambda x: self.q.project_priority_map[x], reverse=True)[0]
        else:
            return None
