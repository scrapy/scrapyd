__author__ = 'drankinn'

import json
import platform
from twisted.python import log
from scrapy.utils.misc import load_object
from scrapyd.interfaces import IPubSub
from zope.interface import implements


class BasePubSub:
    """ Simple Pub Sub pattern where callables are sent messages.
        Tested with LogSubscribers in `scrapyd.pubsub.callbacks`

    """
    implements(IPubSub)

    json_encoder = json.JSONEncoder()
    pubsub_config = {}  # contains values from [pubsub]
    channel_config = {}  # contains values from [channels]
    subscription_channels = {}  # contains {channel,callable} elements
    node_channel = 'scrapyd.node'

    def __init__(self, config, app):
        self.config = config
        self.uri = self.config.get('public_uri', 'http://localhost:6800')
        self.node_id = self.config.get('id', platform.node())
        self.app = app
        self.pubsub_config = config.items('pubsub')
        self.channel_config = config.items('channels')
        for id, channel in self.channel_config:
            if id == 'pub.node.channel':
                self.node_channel = channel
        self.loadDefaultChannels()

    def loadDefaultChannels(self):
        for channel, callbackCls in self.channel_config:
            if channel[:3] == 'sub':
                self.subscribe(channel[4:], load_object(callbackCls))

    def unloadDefaultChannels(self):
        for channel, callbackCls in self.channel_config:
            if channel[:3] == 'sub':
                self.unsubscribe(channel[4:], load_object(callbackCls))

    def publish(self, channel, message):
        self.messageRecieved(channel, message)

    def subscribe(self, channel, callback):
        if callable(callback):
            if channel not in self.subscription_channels:
                self.subscription_channels[channel] = []
            self.unsubscribe(channel, callback)
            self.subscription_channels[channel].append(callback)
            log.msg(format="callback registered on channel %(chnl)r", chnl=channel, system='BasePubSub')

    def unsubscribe(self, channel, callback):
        if channel in self.subscription_channels:
            try:
                self.subscription_channels[channel].remove(callback)
                log.msg(format="callback unregistered on channel %(chnl)r", chnl=channel, system='BasePubSub')
            except ValueError:
                pass

    def messageRecieved(self, channel, message):
        if channel in self.subscription_channels:
            callbacks = self.subscription_channels[channel]
            for callback in callbacks:
                cb = callback(self.app, message)
                cb()

    def registerNode(self):
        message = {
            'event': 'register',
            'node_id': self.node_id,
            'uri': self.uri
        }
        self.publish(self.node_channel, self.json_encoder.encode(message))
