from scrapyd.config import Config
import pika
import pika.spec as spec
from twisted.python import log


class RabbitmqUtils(object):

    channel = None
    connection = None
    
    @staticmethod
    def getConnection():
        
        if RabbitmqUtils.connection == None or not RabbitmqUtils.connection.is_open :
            log.msg('Open connection with RabbitMQ')
            c = Config()
            host = c.get('rabbitmq_host')
            port = c.get('rabbitmq_port')
            vhost = c.get('rabbitmq_vhost')
            user = c.get('rabbitmq_user')
            password = c.get('rabbitmq_password')
            
            credentials = pika.PlainCredentials(user, password)
            parameters = pika.ConnectionParameters(credentials=credentials, host=host, port=int(port), virtual_host=vhost)
            RabbitmqUtils.connection = pika.BlockingConnection(parameters)
        return RabbitmqUtils.connection; 
    
    @staticmethod
    def getChannel():
        if RabbitmqUtils.channel == None or not RabbitmqUtils.connection.is_open :
            con = RabbitmqUtils.getConnection()
            RabbitmqUtils.channel = con.channel();
        return RabbitmqUtils.channel
    
    @staticmethod
    def ack(delivery_tag=None):
        if delivery_tag is not None:
            RabbitmqUtils.getChannel().basic_ack(delivery_tag)
            
    @staticmethod
    def reject(delivery_tag=None):
        if delivery_tag is not None:
            RabbitmqUtils.getChannel().basic_reject(int(delivery_tag), requeue=False )