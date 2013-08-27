__author__ = 'drankinn'

from txredis import RedisSubscriber, RedisSubscriberFactory, RedisClient, RedisClientFactory
from twisted.application.internet import TCPClient
from scrapyd.pubsub.pubsub import BasePubSub


class ScrapyRedisSubscriber(RedisSubscriber):

    def connectionMade(self):
        RedisSubscriber.connectionMade(self)
        self.factory.pubSub.subscriberConnectionMade(self)

    def messageReceived(self, channel, message):
        self.factory.pubSub.messageRecieved(channel, message)

    def channelSubscribed(self, channel, numSubscriptions):
        """
        Called when a channel is subscribed to.
        """
        pass

    def channelUnsubscribed(self, channel, numSubscriptions):
        """
        Called when a channel is unsubscribed from.
        """
        pass

    def channelPatternSubscribed(self, channel, numSubscriptions):
        """
        Called when a channel patern is subscribed to.
        """
        pass

    def channelPatternUnsubscribed(self, channel, numSubscriptions):
        """
        Called when a channel pattern is unsubscribed from.
        """
        pass

    def connectionLost(self, reason):
        RedisSubscriber.connectionLost(self, reason)
        self.factory.pubSub.subscriberConnectionLost()


class ScrapyRedisSubscriberFactory(RedisSubscriberFactory):

    protocol = ScrapyRedisSubscriber

    def __init__(self, pubSub, *args, **kwargs):
        RedisSubscriberFactory.__init__(self, *args, **kwargs)
        self.pubSub = pubSub


class ScrapyRedisClient(RedisClient):

    def connectionMade(self):
        d = RedisClient.connectionMade(self)
        self.factory.pubSub.clientConnectionMade(self)
        return d

    def connectionLost(self, reason):
        d = RedisClient.connectionLost(self, reason)
        self.factory.pubSub.clientConnectionLost()
        return d


class ScrapyRedisClientFactory(RedisClientFactory):

    protocol = ScrapyRedisClient

    def __init__(self, pubSub, *args, **kwargs):
        RedisClientFactory.__init__(self, *args, **kwargs)
        self.pubSub = pubSub


class RedisPubSub(BasePubSub):
    """ replaces the in memory PubSub implementation with redis
        requires host, port as properties in scrapyd.conf under the pubsub section
    """
    pubQueue = []
    client = None
    subscription_active = False
    client_active = False

    def __init__(self, config, app):
        BasePubSub.__init__(self, config, app)
        pubSub = self.pubsub_config
        self.pubsub_config = {}
        for key, val in pubSub:
            self.pubsub_config[key] = val
        self.loadClientService()
        self.loadSubscriptionService()

    def loadSubscriptionService(self):
        subscriberService = TCPClient(self.pubsub_config['host'], int(self.pubsub_config['port']), ScrapyRedisSubscriberFactory(self))
        subscriberService.setServiceParent(self.app)

    def loadClientService(self):
        clientService = TCPClient(self.pubsub_config['host'], int(self.pubsub_config['port']), ScrapyRedisClientFactory(self))
        clientService.setServiceParent(self.app)

    def clientConnectionMade(self, protocol):
        self.client = protocol
        self.client_active = True
        self.emptyPublishQueue()
        self.registerNode()

    def clientConnectionLost(self):
        self.client_active = False
        self.client = None

    def subscriberConnectionMade(self, protocol):
        self.subscription_active = True
        self.subscription = protocol
        self.loadDefaultChannels()

    def subscriberConnectionLost(self):
        self.subscription_active = False
        self.subscription = None
        self.unloadDefaultChannels()

    def publish(self, channel, event):
        if self.client_active:
            self.client.publish(channel, event)
        else:
            self.pubQueue.append({'channel': channel, 'event': event})

    def subscribe(self, channel, callback):
        BasePubSub.subscribe(self, channel, callback)
        if self.subscription_active:
            self.subscription.subscribe(channel)

    def unsubscribe(self, channel, callback):
        BasePubSub.unsubscribe(self, channel, callback)
        if self.subscription_active:
            self.subscription.unsubscribe(channel)

    def emptyPublishQueue(self):
        if self.client_active:
            for node in self.pubQueue:
                self.publish(node['channel'], node['event'])
            self.pubQueue = []

