import sys
from datetime import datetime
from multiprocessing import cpu_count

from twisted.application.service import Service
from twisted.internet import defer, error, protocol, reactor
from twisted.python import log

from scrapyd import __version__
from scrapyd.interfaces import IPoller, IEnvironment, IJobStorage
from scrapyd.orchestrator_client.api_interfaces.JobApi import JobApi


class Launcher(Service):
    name = 'launcher'

    def __init__(self, config, app):
        self.processes = {}
        self.finished = app.getComponent(IJobStorage)
        self.max_proc = self._get_max_proc(config)
        self.runner = config.get('runner', 'scrapyd.runner')
        self.app = app

    def startService(self):
        for slot in range(self.max_proc):
            self._wait_for_project(slot)
        log.msg(format='Scrapyd %(version)s started: max_proc=%(max_proc)r, runner=%(runner)r',
                version=__version__, max_proc=self.max_proc,
                runner=self.runner, system='Launcher')

    def _wait_for_project(self, slot):
        poller = self.app.getComponent(IPoller)
        poller.next().addCallback(self._spawn_process, slot)

    def _spawn_process(self, message, slot):
        msg = native_stringify_dict(message, keys_only=False)
        project = msg['_project']
        args = [sys.executable, '-m', self.runner, 'crawl']
        args += get_crawl_args(msg)
        e = self.app.getComponent(IEnvironment)
        env = e.get_environment(msg, slot)
        env = native_stringify_dict(env, keys_only=False)
        pp = ScrapyProcessProtocol(slot, project, msg['_spider'], \
                                   msg['_job'], env)
        pp.deferred.addBoth(self._process_finished, slot)
        reactor.spawnProcess(pp, sys.executable, args=args, env=env)
        self.processes[slot] = pp

    def _process_finished(self, _, slot):
        process = self.processes.pop(slot)

        process.end_time = datetime.now()
        self.finished.add(process)
        self._wait_for_project(slot)

    def _get_max_proc(self, config):
        max_proc = config.getint('max_proc', 0)
        if not max_proc:
            try:
                cpus = cpu_count()
            except NotImplementedError:
                cpus = 1
            max_proc = cpus * config.getint('max_proc_per_cpu', 4)
        return max_proc


class ScrapyProcessProtocol(protocol.ProcessProtocol):

    def __init__(self, slot, project, spider, job, env):
        self.slot = slot
        self.pid = None
        self.project = project
        self.spider = spider
        self.job = job
        self.start_time = datetime.now()
        self.end_time = None
        self.env = env
        self.logfile = env.get('SCRAPY_LOG_FILE')
        self.itemsfile = env.get('SCRAPY_FEED_URI')
        self.deferred = defer.Deferred()
        self.job_api = JobApi()

    def outReceived(self, data):
        log.msg(data.rstrip(), system="Launcher,%d/stdout" % self.pid)

    def errReceived(self, data):
        log.msg(data.rstrip(), system="Launcher,%d/stderr" % self.pid)

    def connectionMade(self):
        self.pid = self.transport.pid
        try:
            self.job_api.update(self.job, start_time=self.start_time, state="RUNNING")
        except Exception as e:
            log(str(e))
        self.log("Process started: ")

    def processEnded(self, status):
        """
            Add update job state and mark it as finished or crashed, depending on it s final state
        """
        try:
            if isinstance(status.value, error.ProcessDone):
                self.log("Process finished: ")
                self.job_api.update(self.job, state="FINISHED", end_time=datetime.now())
            else:
                self.log("Process died: exitstatus=%r " % status.value.exitCode)
                self.job_api.update(self.job, state="CRASHED", end_time=datetime.now())
            self.deferred.callback(self)
        except Exception as e:
            log.msg(str(e))

    def log(self, action):
        fmt = '%(action)s project=%(project)r spider=%(spider)r job=%(job)r pid=%(pid)r log=%(log)r items=%(items)r'
        log.msg(format=fmt, action=action, project=self.project, spider=self.spider,
                job=self.job, pid=self.pid, log=self.logfile, items=self.itemsfile)
