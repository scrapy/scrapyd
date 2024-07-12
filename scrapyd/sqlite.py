import json
import sqlite3
from datetime import datetime

try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping


class JsonSqliteDict(MutableMapping):
    """SQLite-backed dictionary"""

    def __init__(self, database=None, table="dict"):
        self.database = database or ':memory:'
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        sql = "CREATE TABLE IF NOT EXISTS %s (key blob PRIMARY KEY, value blob)" % table
        self.conn.execute(sql)

    def __getitem__(self, key):
        key = self.encode(key)
        sql = "SELECT value FROM %s WHERE key = ?" % self.table
        value = self.conn.execute(sql, (key,)).fetchone()
        if value:
            return self.decode(value[0])
        raise KeyError(key)

    def __setitem__(self, key, value):
        key, value = self.encode(key), self.encode(value)
        sql = "INSERT OR REPLACE INTO %s (key, value) VALUES (?, ?)" % self.table
        self.conn.execute(sql, (key, value))
        self.conn.commit()

    def __delitem__(self, key):
        key = self.encode(key)
        sql = "DELETE FROM %s WHERE key = ?" % self.table
        self.conn.execute(sql, (key,))
        self.conn.commit()

    def __len__(self):
        sql = "SELECT COUNT(*) FROM %s" % self.table
        return self.conn.execute(sql).fetchone()[0]

    def __iter__(self):
        for key in self.iterkeys():
            yield key

    def iterkeys(self):
        sql = "SELECT key FROM %s" % self.table
        return (self.decode(row[0]) for row in self.conn.execute(sql))

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        sql = "SELECT value FROM %s" % self.table
        return (self.decode(row[0]) for row in self.conn.execute(sql))

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        sql = "SELECT key, value FROM %s" % self.table
        return ((self.decode(row[0]), self.decode(row[1])) for row in self.conn.execute(sql))

    def items(self):
        return list(self.iteritems())

    def encode(self, obj):
        return sqlite3.Binary(json.dumps(obj).encode('ascii'))

    def decode(self, obj):
        return json.loads(bytes(obj).decode('ascii'))


class JsonSqlitePriorityQueue(object):
    """SQLite priority queue. It relies on SQLite concurrency support for
    providing atomic inter-process operations.
    """

    def __init__(self, database=None, table="queue"):
        self.database = database or ':memory:'
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        sql = "CREATE TABLE IF NOT EXISTS %s (id integer PRIMARY KEY, priority real key, message blob)" % table
        self.conn.execute(sql)

    def put(self, message, priority=0.0):
        args = (priority, self.encode(message))
        sql = "INSERT INTO %s (priority, message) VALUES (?, ?)" % self.table
        self.conn.execute(sql, args)
        self.conn.commit()

    def pop(self):
        sql = "SELECT id, message FROM %s ORDER BY priority DESC LIMIT 1" % self.table
        idmsg = self.conn.execute(sql).fetchone()
        if idmsg is None:
            return
        id, msg = idmsg
        sql = "DELETE FROM %s WHERE id = ?" % self.table
        c = self.conn.execute(sql, (id,))
        if not c.rowcount:  # record vanished, so let's try again
            self.conn.rollback()
            return self.pop()
        self.conn.commit()
        return self.decode(msg)

    def remove(self, func):
        sql = "SELECT id, message FROM %s" % self.table
        n = 0
        for id, msg in self.conn.execute(sql):
            if func(self.decode(msg)):
                sql = "DELETE FROM %s WHERE id = ?" % self.table
                c = self.conn.execute(sql, (id,))
                if not c.rowcount:  # record vanished, so let's try again
                    self.conn.rollback()
                    return self.remove(func)
                n += 1
        self.conn.commit()
        return n

    def clear(self):
        self.conn.execute("DELETE FROM %s" % self.table)
        self.conn.commit()

    def __len__(self):
        sql = "SELECT COUNT(*) FROM %s" % self.table
        return self.conn.execute(sql).fetchone()[0]

    def __iter__(self):
        sql = "SELECT message, priority FROM %s ORDER BY priority DESC" % self.table
        return ((self.decode(message), priority) for message, priority in self.conn.execute(sql))

    def encode(self, obj):
        return sqlite3.Binary(json.dumps(obj).encode('ascii'))

    def decode(self, text):
        return json.loads(bytes(text).decode('ascii'))


class SqliteFinishedJobs(object):
    """SQLite finished jobs. """

    def __init__(self, database=None, table="finished_jobs"):
        self.database = database or ':memory:'
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        sql = "CREATE TABLE IF NOT EXISTS %s (id integer PRIMARY KEY, " \
            "project text, spider text, job text, start_time datetime, end_time datetime)" % table
        self.conn.execute(sql)

    def add(self, job):
        args = (job.project, job.spider, job.job, job.start_time, job.end_time)
        sql = "INSERT INTO %s (project, spider, job, start_time, end_time) VALUES (?, ?, ?, ?, ?)" % self.table
        self.conn.execute(sql, args)
        self.conn.commit()

    def clear(self, finished_to_keep=None):
        w = ""
        if finished_to_keep:
            limit = len(self) - finished_to_keep
            if limit <= 0:
                return  # nothing to delete
            w = "WHERE id <= " \
                "(SELECT max(id) FROM (SELECT id FROM %s ORDER BY end_time LIMIT %d))" % (self.table, limit)
        sql = "DELETE FROM %s %s" % (self.table, w)
        self.conn.execute(sql)
        self.conn.commit()

    def __len__(self):
        sql = "SELECT COUNT(*) FROM %s" % self.table
        return self.conn.execute(sql).fetchone()[0]

    def __iter__(self):
        sql = "SELECT project, spider, job, start_time, end_time FROM %s ORDER BY end_time DESC" % self.table
        return ((j[0], j[1], j[2],
                datetime.strptime(j[3], "%Y-%m-%d %H:%M:%S.%f"),
                datetime.strptime(j[4], "%Y-%m-%d %H:%M:%S.%f")) for j in self.conn.execute(sql))
