import json
import datetime
import logging
from scrapyd.postgres import Postgres

logger = logging.getLogger(__name__)

class MysqlSchedulePersist():
    
    def __init__(self):
        self.table = 'schedule'
        #Postgres.__init__(self, table=self.table)
        self.logger = logger
        
    def add(self, project, spider_name, **spider_args):
        d = spider_args.copy()
        jobid = d['_job']
        del d['_job']
        del d['settings']
        data = json.dumps(d)
        query = "INSERT INTO schedule" + \
                "(jobid, project, spider, " \
                + "params, date) " \
                + " VALUES('" + jobid + "','" \
                + project + "','" \
                + spider_name + "','" \
                + data + "','" \
                + unicode(datetime.datetime.now()) + "')" 
        Postgres.execute(query);
        
    def setStart(self, jobid):
        query = "update schedule set start_time = '" +\
                unicode(datetime.datetime.now()) +"' " +\
                " where jobid = '"+ jobid +"'"
        Postgres.execute(query);

                
    def setEnd(self, jobid, error_count, warn_count, item_count, request_count):
        query = "update schedule set end_time = '"          +\
                unicode(datetime.datetime.now()) +"', "     +\
                " error_count = " + str(error_count) + ", "      +\
                " warn_count = " + str(warn_count) + ", "        +\
                " item_count = " + str(item_count) + ", "        +\
                " request_count = " + str(request_count) + " "  +\
                " where jobid = '"+ jobid +"'"
        Postgres.execute(query);
