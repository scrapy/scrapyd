import psycopg2
import json
import datetime
import logging

logger = logging.getLogger(__name__)

class MysqlSchedulePersist(object):
    
    def __init__(self, config):
        
        self.db_name = config.get('postgres_db_name')
        self.host = config.get('postgres_host')
        self.port = config.get('postgres_port')
        self.user = config.get('postgres_user')
        self.password = config.get('postgres_password')
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