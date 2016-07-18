import psycopg2
from scrapyd.config import Config
import cPickle
import json
from UserDict import DictMixin
import logging

from twisted.python import log
import sys

reload(sys)  
sys.setdefaultencoding('utf-8')

logger = logging.getLogger(__name__)


class Postgres(object):
    
    def __init__(self, database=None, table="dict"):
        c = Config()
        self.db_name = c.get('postgres_db_name')
        self.host = c.get('postgres_host')
        self.port = c.get('postgres_port')
        self.user = c.get('postgres_user')
        self.password = c.get('postgres_password')
        self.con = None
        
    def connect(self, retries=0):
        try:
            log.msg('Connecting to Database')
            self.con = psycopg2.connect(database=self.db_name,
                                        user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        port=self.port)
            
            self.con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except Exception as e:
            log.msg("Error to connect to database... ")
            if retries < 10 :
                logger.info("Retrying... ")
                self.connect(retries+1)
            else:
                raise e

    def execute(self, sql, param = None, query=False, uniqueResult=False):
        if self.con is None or self.con.closed != 0 :
            self.connect()
        cur = self.con.cursor()
        result = None
        try:
            log.msg("Executing query: " + sql)
            if(param is not None):
                cur.execute(sql, param)
            else:
                cur.execute(sql)
                
            if(not query):
                result = None
            elif(uniqueResult):
                result = cur.fetchone()
            else:
                result = cur.fetchall()
            #self.con.commit()
        except psycopg2.DatabaseError, e:
            if e.pgcode == '23505':  # Duplicated Item Code
                #self.con.rollback()
                log.msg('Record already exist, updating it')
            else:
                log.msg('Psycopg2 Error :' + e.pgerror)
                #self.con.rollback()
        finally:
            if cur:
                cur.close()
        return result
    

class PostgresDict(DictMixin, Postgres):
    """Postgres-backed dictionary"""

    def __init__(self, database=None, table="dict", project=None, create=True):
        Postgres.__init__(self, database, table)
        self.table = table
        self.project = project
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        q = "create table if not exists %s (key text, value text, PRIMARY KEY (key))" \
            % table
        self.execute(q)
        
    def __getitem__(self, key):
        key = self.encode(key)
        q = "select value from "+self.table+" where key=%s "  
        value = self.execute(q, (key,), True, True)
        if value:
            return self.decode(value[0])
        raise KeyError(key)

    def __setitem__(self, key, value):
        key, value = self.encode(key), self.encode(value)
        q = "insert into %s (key, value) values (%%s,%%s)" % self.table  
        self.execute(q, (key, value))

    def __delitem__(self, key):
        key = self.encode(key)
        q = "delete from "+self.table+" where key=%s"
        self.execute(q, (key,))

    def iterkeys(self):
        q = "select key from %s" % self.table
        return (self.decode(x[0]) for x in self.execute(q, None, True, False))

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        q = "select value from %s" % self.table
        return (self.decode(x[0]) for x in self.execute(q, None, True, False))

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        q = "select key, value from %s" % self.table
        return ((self.decode(x[0]), self.decode(x[1])) for x in self.execute(q, None, True, False))

    def items(self):
        return list(self.iteritems())

    def encode(self, obj):
        return obj

    def decode(self, text):
        return text


class PicklePostgresDict(PostgresDict):

    def encode(self, obj):
        return buffer(cPickle.dumps(obj, protocol=2))

    def decode(self, text):
        return cPickle.loads(str(text))


class JsonPostgresDict(PostgresDict):

    def encode(self, obj):
        return json.dumps(obj)

    def decode(self, text):
        return json.loads(text)



class PostgresPriorityQueue(Postgres):
    """SQLite priority queue. It relies on SQLite concurrency support for
    providing atomic inter-process operations.
    """

    def __init__(self, database=None, table="queue", project=None):
        self.database = database or ':memory:'
        self.table = table
        self.project = project
        Postgres.__init__(self, database, table)
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        q = "create table if not exists %s (id serial, project character varying, " \
            "priority real, message text, primary key(id))" % table
        self.execute(q)
        
    def put(self, message, priority=0.0):
        args = (self.project, priority, self.encode(message))
        log.msg(args)
        q = "insert into %s (project, priority, message) values (%%s,%%s,%%s)" % self.table
        self.execute(q, args)

    def pop(self):
        q = "select id, message from %s where project = %%s order by priority desc limit 1" \
            % self.table
        idmsg = self.execute(q, (self.project,), True, True)
        if idmsg is None:
            return
        id, msg = idmsg
        q = "delete from %s where id=%%s" % self.table
        c = self.execute(q, (id,))
        #if not c.rowcount: # record vanished, so let's try again
            #return self.pop()
        return self.decode(msg)

    def remove(self, func):
        q = "select id, message from %s where project = %%s" % self.table
        n = 0
        for id, msg in self.execute(q, (self.project,), True, False):
            if func(self.decode(msg)):
                q = "delete from %s where id=%%s" % self.table
                c = self.execute(q, (id,))
                #if not c.rowcount: # record vanished, so let's try again
                #   return self.remove(func)
                n += 1
        return n

    def clear(self):
        self.execute("delete from %s where project = %%s" % self.table, (self.project,))

    def __len__(self):
        q = "select count(*) from %s where project = %%s" % self.table
        n = self.execute(q, (self.project,), True, True)
        return int(n[0])

    def __iter__(self):
        q = "select message, priority from %s where project = %%s order by priority desc" % \
            self.table
        return ((self.decode(x), y) for x, y in self.execute(q, (self.project,), True, False))

    def encode(self, obj):
        return obj

    def decode(self, text):
        return text


class PicklePostgresPriorityQueue(PostgresPriorityQueue):

    def encode(self, obj):
        return buffer(cPickle.dumps(obj, protocol=2))

    def decode(self, text):
        return cPickle.loads(str(text))


class JsonPostgresPriorityQueue(PostgresPriorityQueue):

    def encode(self, obj):
        return json.dumps(obj)

    def decode(self, text):
        return json.loads(text)

