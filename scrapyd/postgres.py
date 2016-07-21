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
    con = None
        
    @staticmethod
    def connect(retries=0):
        c = Config()
        db_name = c.get('postgres_db_name')
        host = c.get('postgres_host')
        port = c.get('postgres_port')
        user = c.get('postgres_user')
        password = c.get('postgres_password')
        Postgres.con = None
        try:
            log.msg('Connecting to Database')
            Postgres.con = psycopg2.connect(database=db_name,
                                        user=user,
                                        password=password,
                                        host=host,
                                        port=port)
            
            Postgres.con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        except Exception as e:
            log.msg("Error to connect to database... ")
            if retries < 10 :
                logger.info("Retrying... ")
                Postgres.connect(retries+1)
            else:
                raise e
            
    @staticmethod
    def execute(sql, param = None, query=False, uniqueResult=False):
        if Postgres.con is None or Postgres.con.closed != 0 :
            Postgres.connect()
        cur = Postgres.con.cursor()
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
        except psycopg2.DatabaseError, e:
            if e.pgcode == '23505':  # Duplicated Item Code
                log.msg('Record already exist, updating it')
            else:
                log.msg('Psycopg2 Error :' + e.pgerror)
        finally:
            if cur:
                cur.close()
        return result
    

class PostgresDict(DictMixin):
    """Postgres-backed dictionary"""

    def __init__(self, database=None, table="dict", project=None, create=True):
        #Postgres.__init__(self, database, table)
        self.table = table
        self.project = project
        self.table = table
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        q = "create table if not exists %s (key text, value text, PRIMARY KEY (key))" \
            % table
        #self.execute(q)
        
    def __getitem__(self, key):
        key = self.encode(key)
        q = "select value from "+self.table+" where key=%s "  
        value = Postgres.execute(q, (key,), True, True)
        if value:
            return self.decode(value[0])
        raise KeyError(key)

    def __setitem__(self, key, value):
        key, value = self.encode(key), self.encode(value)
        q = "insert into %s (key, value) values (%%s,%%s)" % self.table  
        Postgres.execute(q, (key, value))

    def __delitem__(self, key):
        key = self.encode(key)
        q = "delete from "+self.table+" where key=%s"
        Postgres.execute(q, (key,))

    def iterkeys(self):
        q = "select key from %s" % self.table
        return (self.decode(x[0]) for x in Postgres.execute(q, None, True, False))

    def keys(self):
        return list(self.iterkeys())

    def itervalues(self):
        q = "select value from %s" % self.table
        return (self.decode(x[0]) for x in Postgres.execute(q, None, True, False))

    def values(self):
        return list(self.itervalues())

    def iteritems(self):
        q = "select key, value from %s" % self.table
        return ((self.decode(x[0]), self.decode(x[1])) for x in Postgres.execute(q, None, True, False))

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



class PostgresPriorityQueue(object):
    """SQLite priority queue. It relies on SQLite concurrency support for
    providing atomic inter-process operations.
    """

    def __init__(self, database=None, table="queue", project=None):
        self.database = database or ':memory:'
        self.table = table
        self.project = project
        #Postgres.__init__(self, database, table)
        # about check_same_thread: http://twistedmatrix.com/trac/ticket/4040
        q = "create table if not exists %s (id serial, project character varying, " \
            "priority real, message text, primary key(id))" % table
        #self.execute(q)
        
    def put(self, message, priority=0.0):
        args = (self.project, priority, self.encode(message))
        log.msg(args)
        q = "insert into %s (project, priority, message) values (%%s,%%s,%%s)" % self.table
        Postgres.execute(q, args)

    def pop(self):
        q = "select id, message from %s where project = %%s order by priority desc limit 1" \
            % self.table
        idmsg = Postgres.execute(q, (self.project,), True, True)
        if idmsg is None:
            return
        id, msg = idmsg
        q = "delete from %s where id=%%s" % self.table
        c = Postgres.execute(q, (id,))
        #if not c.rowcount: # record vanished, so let's try again
            #return self.pop()
        return self.decode(msg)

    def remove(self, func):
        q = "select id, message from %s where project = %%s" % self.table
        n = 0
        for id, msg in Postgres.execute(q, (self.project,), True, False):
            if func(self.decode(msg)):
                q = "delete from %s where id=%%s" % self.table
                c = Postgres.execute(q, (id,))
                #if not c.rowcount: # record vanished, so let's try again
                #   return self.remove(func)
                n += 1
        return n

    def clear(self):
        Postgres.execute("delete from %s where project = %%s" % self.table, (self.project,))

    def __len__(self):
        q = "select count(*) from %s where project = %%s" % self.table
        n = Postgres.execute(q, (self.project,), True, True)
        return int(n[0])

    def __iter__(self):
        q = "select message, priority from %s where project = %%s order by priority desc" % \
            self.table
        return ((self.decode(x), y) for x, y in Postgres.execute(q, (self.project,), True, False))

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

