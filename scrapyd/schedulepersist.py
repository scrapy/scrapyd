import psycopg2
import json
import datetime
import logging
from scrapyd.config import Config

logger = logging.getLogger(__name__)

class MysqlSchedulePersist(object):
    
    def __init__(self):
        c = Config()
        self.db_name = c.get('postgres_db_name')
        self.host = c.get('postgres_host')
        self.port = c.get('postgres_port')
        self.user = c.get('postgres_user')
        self.password = c.get('postgres_password')
        self.table = 'schedule'
        self.con = None
        self.cur = None
        self.logger = logger
        
    def connect(self, retries=0):
        try:
            self.logger.info('Connecting to Database')
            self.con = psycopg2.connect(database=self.db_name,
                                        user=self.user,
                                        password=self.password,
                                        host=self.host,
                                        port=self.port)
            self.cur = self.con.cursor()
        except Exception as e:
            self.logger.info("Error to connect to database... ")
            if retries < 10 :
                self.logger.info("Retrying... ")
                self.connect(retries+1)
            else:
                raise e
            
    def add(self, project, spider_name, **spider_args):
        d = spider_args.copy()
        jobid = d['_job']
        del d['_job']
        del d['settings']
        if self.con is None or self.con.closed != 0 or self.cur is None:
            self.connect()
        try:
            data = json.dumps(d)
            self.logger.info(data)
            query = "INSERT INTO schedule" + \
                    "(jobid, project, spider, " \
                    + "params, date) " \
                    + " VALUES('" + jobid + "','" \
                    + project + "','" \
                    + spider_name + "','" \
                    + data + "','" \
                    + unicode(datetime.datetime.now()) + "')" 
                    
            self.logger.info("Executing query: " + query)
            self.cur.execute(query)
            self.con.commit()

        except psycopg2.DatabaseError, e:
            if e.pgcode == '23505':  # Duplicated Item Code
                self.logger.info('Schedule already exist, updating it')
                self.con.rollback()
            elif self.con:
                self.con.rollback()
                self.con.close()
                self.logger.info('Psycopg2 Error :' + e.pgerror)
                self.con = None
                self.cur = None
        finally:
            if self.con:
                self.con.close()
                
    def setStart(self, jobid):
        query = "update schedule set start_time = '" +\
                unicode(datetime.datetime.now()) +"' " +\
                " where jobid = '"+ jobid +"'"
        self.executeQuey(query);

                
    def setEnd(self, jobid, error_count, warn_count, item_count, request_count):
        query = "update schedule set end_time = '"          +\
                unicode(datetime.datetime.now()) +"', "     +\
                " error_count = " + str(error_count) + ", "      +\
                " warn_count = " + str(warn_count) + ", "        +\
                " item_count = " + str(item_count) + ", "        +\
                " request_count = " + str(request_count) + " "  +\
                " where jobid = '"+ jobid +"'"
        self.executeQuey(query);
        
                
    def executeQuey(self, query):
        if self.con is None or self.con.closed != 0 or self.cur is None:
            self.connect()
        try:
            self.logger.info("Executing query: " + query)
            self.cur.execute(query)
            self.con.commit()
        except psycopg2.DatabaseError, e:
            self.con.rollback()
            self.con.close()
            self.logger.info('Psycopg2 Error :' + e.pgerror)
            self.con = None
            self.cur = None
        finally:
            if self.con:
                self.con.close()