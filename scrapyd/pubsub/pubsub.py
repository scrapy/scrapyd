__author__ = 'drankinn'

from twisted.python import log
from scrapy.utils.misc import load_object
from scrapyd.interfaces import IPubSub
from zope.interface import implements


class BasePubSub:
    """ Simple Pub Sub pattern where callables are sent messages.
        Tested with LogSubscribers in `scrapyd.pubsub.callbacks`

    """
    implements(IPubSub)

    pubsub_config = {}  # contains values from [pubsub]
    channel_config = {}  # contains values from [channels]
    channels = {}  # contains {channel,callable} elements

    def __init__(self, config, app):
        self.config = config
        self.app = app
        self.pubsub_config = config.items('pubsub')
        self.channel_config = config.items('channels')
        self.loadDefaultChannels()

    def loadDefaultChannels(self):
        for channel, callbackCls in self.channel_config:
            self.subscribe(channel, load_object(callbackCls))

    def unloadDefaultChannels(self):
        for channel, callbackCls in self.channel_config:
            self.unsubscribe(channel, load_object(callbackCls))

    def publish(self, channel, message):
        self.messageRecieved(channel, message)

    def subscribe(self, channel, callback):
        if callable(callback):
            if channel not in self.channels:
                self.channels[channel] = []
            self.unsubscribe(channel, callback)
            self.channels[channel].append(callback)
            log.msg(format="callback registered on channel %(chnl)r", chnl=channel, system='BasePubSub')

    def unsubscribe(self, channel, callback):
        if channel in self.channels:
            try:
                self.channels[channel].remove(callback)
                log.msg(format="callback unregistered on channel %(chnl)r", chnl=channel, system='BasePubSub')
            except ValueError:
                pass

    def messageRecieved(self, channel, message):
        if channel in self.channels:
            callbacks = self.channels[channel]
            for callback in callbacks:
                cb = callback(self.app, message)
                cb()

