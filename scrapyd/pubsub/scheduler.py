import json
from twisted.application.service import IServiceCollection
from zope.interface import implements

from scrapyd.interfaces import ISpiderScheduler
from scrapyd.utils import get_spider_queues
from scrapyd.interfaces import IPubSub


class Scheduler(object):

    implements(ISpiderScheduler)

    channel = 'scrapyd.schedule'
    json_encoder = json.JSONEncoder()

    def __init__(self, config, app):
        self.app = app
        self.config = config
        self.update_projects()

    def schedule(self, project, spider_name, **spider_args):
        q = self.queues[project]
        q.add(spider_name, **spider_args)
        self.publish(project, spider_name, **spider_args)

    def list_projects(self):
        return self.queues.keys()

    def update_projects(self):
        self.queues = get_spider_queues(self.config)

    @property
    def launcher(self):
        app = IServiceCollection(self.app, self.app)
        return app.getServiceNamed('launcher')

    @property
    def pubsub(self):
        return self.app.getComponent(IPubSub)

    def publish(self, project, spider, **args):
        message = {
            'event': 'scheduled',
            'status': 'ok',
            'project': project,
            'spider': spider,
            'job': args['_job']

        }
        self.pubsub.publish(self.launcher.channel, self.json_encoder.encode(message))