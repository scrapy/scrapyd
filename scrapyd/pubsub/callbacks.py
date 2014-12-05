import json
import pprint
import uuid
from scrapyd.interfaces import ISpiderScheduler, IPubSub

__author__ = 'drankinn'

from twisted.python import log


class PubSubCallable:

    system = 'LogCallable'

    def __init__(self, app, message):
        self.app = app
        self.message = message

    def __call__(self):
        log.msg(format="%(msg)s", msg=self.message, system='PubSub:'+self.system)


class LogScheduler(PubSubCallable):
    system = 'Scheduler'


class LogLauncher(PubSubCallable):
    system = 'LogLauncher'


class ScrapyScheduler(PubSubCallable):
    system = 'ScrapyScheduler'
    json_decoder = json.JSONDecoder()
    json_encoder = json.JSONEncoder()

    @property
    def scheduler(self):
        return self.app.getComponent(ISpiderScheduler)

    @property
    def pubsub(self):
        return self.app.getComponent(IPubSub)

    def __call__(self):
        print self.message
        try:
            args = self.json_decoder.decode(self.message)
            project = args.pop('project')
            spider = args.pop('spider')
            if args['_job'] is None:
                args['_job'] = uuid.uuid1().hex
            self.scheduler.schedule(project, spider, **args)
        except ValueError:
            pass