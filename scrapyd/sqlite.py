import datetime
import json
import os
import sqlite3


# The database argument is "jobs" (in SqliteJobStorage), or a project (in SqliteSpiderQueue) from get_spider_queues(),
# which gets projects from get_project_list(), which gets projects from egg storage. We check for directory traversal
# in egg storage, instead.
def initialize(cls, config, database, table):
    dbs_dir = config.get("dbs_dir", "dbs")
    if dbs_dir == ":memory:":
        connection_string = dbs_dir
    else:
        if not os.path.exists(dbs_dir):
            os.makedirs(dbs_dir)
        connection_string = os.path.join(dbs_dir, f"{database}.db")

    return cls(connection_string, table)


# https://docs.python.org/3/library/sqlite3.html#sqlite3-adapter-converter-recipes
def adapt_datetime(val):
    return val.strftime("%Y-%m-%d %H:%M:%S.%f")


def convert_datetime(val):
    return datetime.datetime.strptime(val.decode(), "%Y-%m-%d %H:%M:%S.%f")


sqlite3.register_adapter(datetime.datetime, adapt_datetime)
sqlite3.register_converter("datetime", convert_datetime)


class SqliteMixin:
    def __init__(self, database, table):
        self.database = database or ":memory:"
        self.table = table
        # Regarding check_same_thread, see http://twistedmatrix.com/trac/ticket/4040
        self.conn = sqlite3.connect(self.database, check_same_thread=False)

    def __len__(self):
        return self.conn.execute(f"SELECT COUNT(*) FROM {self.table}").fetchone()[0]

    # SQLite JSON is enabled by default since 3.38.0 (2022-02-22), and JSONB is available since 3.45.0 (2024-01-15).
    # https://sqlite.org/json1.html
    def encode(self, obj):
        return sqlite3.Binary(json.dumps(obj).encode("ascii"))

    def decode(self, obj):
        return json.loads(bytes(obj).decode("ascii"))


class JsonSqlitePriorityQueue(SqliteMixin):
    """
    SQLite priority queue. It relies on SQLite concurrency support for providing atomic inter-process operations.

    .. versionadded:: 1.0.0
    """

    def __init__(self, database=None, table="queue"):
        super().__init__(database, table)

        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table} (id integer PRIMARY KEY, priority real key, message blob)"
        )

    def put(self, message, priority=0.0):
        self.conn.execute(
            f"INSERT INTO {self.table} (priority, message) VALUES (?, ?)",
            (priority, self.encode(message)),
        )
        self.conn.commit()

    def pop(self):
        row = self.conn.execute(f"SELECT id, message FROM {self.table} ORDER BY priority DESC LIMIT 1").fetchone()
        if row is None:
            return None
        _id, message = row

        # If a row vanished, try again.
        if not self.conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (_id,)).rowcount:
            self.conn.rollback()
            return self.pop()

        self.conn.commit()
        return self.decode(message)

    def remove(self, func):
        deleted = 0
        for _id, message in self.conn.execute(f"SELECT id, message FROM {self.table}"):
            if func(self.decode(message)):
                # If a row vanished, try again.
                if not self.conn.execute(f"DELETE FROM {self.table} WHERE id = ?", (_id,)).rowcount:
                    self.conn.rollback()
                    return self.remove(func)
                deleted += 1

        self.conn.commit()
        return deleted

    def clear(self):
        self.conn.execute(f"DELETE FROM {self.table}")
        self.conn.commit()

    def __iter__(self):
        return (
            (self.decode(message), priority)
            for message, priority in self.conn.execute(
                f"SELECT message, priority FROM {self.table} ORDER BY priority DESC"
            )
        )


class SqliteFinishedJobs(SqliteMixin):
    """
    SQLite finished jobs.

    .. versionadded:: 1.3.0
       Job storage was previously in-memory only.
    """

    def __init__(self, database=None, table="finished_jobs"):
        super().__init__(database, table)

        self.conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table} "
            "(id integer PRIMARY KEY, project text, spider text, job text, start_time datetime, end_time datetime)"
        )

    def add(self, job):
        self.conn.execute(
            f"INSERT INTO {self.table} (project, spider, job, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
            (job.project, job.spider, job.job, job.start_time, job.end_time),
        )
        self.conn.commit()

    def clear(self, finished_to_keep=None):
        where = ""
        if finished_to_keep:
            limit = len(self) - finished_to_keep
            if limit <= 0:
                return  # nothing to delete
            where = f"WHERE id <= (SELECT max(id) FROM (SELECT id FROM {self.table} ORDER BY end_time LIMIT {limit}))"

        self.conn.execute(f"DELETE FROM {self.table} {where}")
        self.conn.commit()

    def __iter__(self):
        return (
            (
                project,
                spider,
                job,
                datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f"),
                datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S.%f"),
            )
            for project, spider, job, start_time, end_time in self.conn.execute(
                f"SELECT project, spider, job, start_time, end_time FROM {self.table} ORDER BY end_time DESC"
            )
        )
