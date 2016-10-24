import datetime
import uuid
from scrapyd.webservice import WsResource
from scrapyd.utils import get_spider_list


class Schedule(WsResource):

    def render_POST(self, txrequest):
        settings = txrequest.args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in txrequest.args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        version = args.get('_version', '')
        spiders = get_spider_list(project, version=version)
        if not spider in spiders:
            return {"status": "error", "message": "spider '%s' not found" % spider}
        args['settings'] = settings
        jobid = args.pop('jobid', uuid.uuid1().hex)
        args['_job'] = jobid
        self.root.scheduler.schedule(project, spider, **args)
        settings['LOG_FILE'] = self._log_path(self.config.logs_dir,
                                              self.config.log_filename_fmt,
                                              # TODO: tie the config object to the webservices? to the website? to the app?
                                              project, spider, jobid)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}

    def _log_path(self, logs_dir, log_filename_fmt, project, spider, jobid):

        now = datetime.datetime.now()
        format_args = {'project': project, 'spider': spider, 'job': jobid,
                       'Y': now.year,      'm': now.month,   'd': now.day,
                       'H': now.hour,      'M': now.minute,  'S': now.second}
        filename = log_filename_fmt.format(**format_args)

        full_filename = os.path.join(self.logs_dir, filename)

        log_dir = os.path.dirname(full_filename)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return full_filename
