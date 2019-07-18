import os
import sqlite3

from scrapyd.sqlite import JsonSqlitePriorityQueue


class FixJsonSqlitePriorityQueue(JsonSqlitePriorityQueue):
    """SQLite priority queue. It relies on SQLite concurrency support for
    providing atomic inter-process operations.
    """
    project_priority_map = {}

    def __init__(self, database=None, table="queue"):
        self.database = database or ':memory:'
        self.table = table
        if database:
            dbname = os.path.split(database)[-1]
            self.project = os.path.splitext(dbname)[0]
        else:
            self.project = self.database
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        q = "create table if not exists %s (id integer primary key, " \
            "priority real key, message blob, insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)" % table
        self.conn.execute(q)
        self.create_triggers()
        self.update_project_priority_map()

    def create_triggers(self):
        self.conn.create_function("update_project_priority_map", 0, self.update_project_priority_map)
        for action in ['INSERT', 'UPDATE', 'DELETE']:
            name = 'trigger_on_%s' % action.lower()
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS %s AFTER %s ON %s
                BEGIN
                    SELECT update_project_priority_map();
                END;
            """ % (name, action, self.table))

    def update_project_priority_map(self):
        q = "select priority, strftime('%%s', insert_time) from %s order by priority desc limit 1" \
            % self.table
        result = self.conn.execute(q).fetchone()
        if result is None:
            self.project_priority_map.pop(self.project, None)
        else:
            self.project_priority_map[self.project] = (result[0], -int(result[-1]))
