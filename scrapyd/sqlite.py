import sqlite3
import json
import os
try:
    from collections.abc import MutableMapping
except ImportError:
    from collections import MutableMapping
import six


from ._deprecate import deprecate_class


class JsonSqliteDict(MutableMapping):
    """SQLite-backed dictionary"""

    def __init__(self, database=None, table="dict"):
        self.database = database or ':memory:'
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)
        q = "create table if not exists %s (key blob primary key, value blob)" \
            % table
        self.conn.execute(q)

    def __getitem__(self, key):
        key = self.encode(key)
        q = "select value from %s where key=?" % self.table
        value = self.conn.execute(q, (key,)).fetchone()
        if value:
            return self.decode(value[0])
        raise KeyError(key)

    def __setitem__(self, key, value):
        key, value = self.encode(key), self.encode(value)
        q = "insert or replace into %s (key, value) values (?,?)" % self.table
        self.conn.execute(q, (key, value))
        self.conn.commit()

    def __delitem__(self, key):
        key = self.encode(key)
        q = "delete from %s where key=?" % self.table
        self.conn.execute(q, (key,))
        self.conn.commit()

    def __len__(self):
        q = "select count(*) from %s" % self.table
        return self.conn.execute(q).fetchone()[0]

    def __iter__(self):
        for k in self.iterkeys():
            yield k

    def iterkeys(self):
        q = "select key from %s" % self.table
        return (self.decode(x[0]) for x in self.conn.execute(q))

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        q = "select value from %s" % self.table
        return (self.decode(x[0]) for x in self.conn.execute(q))

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        q = "select key, value from %s" % self.table
        return ((self.decode(x[0]), self.decode(x[1])) for x in self.conn.execute(q))

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
            "priority real key, message blob, insert_time TIMESTAMP)" % table
        self.conn.execute(q)
        self.create_triggers()
        self.update_project_priority_map()

    def put(self, message, priority=0.0):
        args = (priority, self.encode(message))
        q = "insert into %s (priority, message, insert_time) values (?,?, CURRENT_TIMESTAMP)" \
            % self.table
        self.conn.execute(q, args)
        self.conn.commit()

    def pop(self):
        q = "select id, message from %s order by priority desc limit 1" \
            % self.table
        idmsg = self.conn.execute(q).fetchone()
        if idmsg is None:
            return
        id, msg = idmsg
        q = "delete from %s where id=?" % self.table
        c = self.conn.execute(q, (id,))
        if not c.rowcount: # record vanished, so let's try again
            self.conn.rollback()
            return self.pop()
        self.conn.commit()
        return self.decode(msg)

    def remove(self, func):
        q = "select id, message from %s" % self.table
        n = 0
        for id, msg in self.conn.execute(q):
            if func(self.decode(msg)):
                q = "delete from %s where id=?" % self.table
                c = self.conn.execute(q, (id,))
                if not c.rowcount: # record vanished, so let's try again
                    self.conn.rollback()
                    return self.remove(func)
                n += 1
        self.conn.commit()
        return n

    def clear(self):
        self.conn.execute("delete from %s" % self.table)
        self.conn.commit()

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

    def __len__(self):
        q = "select count(*) from %s" % self.table
        return self.conn.execute(q).fetchone()[0]

    def __iter__(self):
        q = "select message, priority from %s order by priority desc" % \
            self.table
        return ((self.decode(x), y) for x, y in self.conn.execute(q))

    def encode(self, obj):
        return sqlite3.Binary(json.dumps(obj).encode('ascii'))

    def decode(self, text):
        return json.loads(bytes(text).decode('ascii'))
