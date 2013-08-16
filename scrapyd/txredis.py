from txredis import RedisSubscriberFactory, RedisSubscriber


class ScrapyRedisSubscriber(RedisSubscriber):


    def __init__(self, pubsub, *args, **kwargs):
        self.pubsub = pubsub
        RedisSubscriber.__init__(self, *args, **kwargs)
class ScrapyRedisSubscriberFactory(RedisSubscriberFactory):
    protocol = ScrapyRedisSubscriber