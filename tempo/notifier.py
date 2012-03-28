import datetime
import logging
import uuid

from tempo import config
from tempo import queue
from tempo.openstack.common import cfg

CFG = config.CFG

notifier_opts = [
    cfg.StrOpt('driver',
               default='logging',
               help='Driver to be used for notification'),
    cfg.StrOpt('rabbit_topic',
               default='tempo_notifications',
               help='Topic used for rabbit notifications'),
    cfg.StrOpt('level',
               default='INFO',
               help='What priority should be used for notifications')
]

notifier_group = cfg.OptGroup(name='notifier', title='Notifier options')
CFG.register_group(notifier_group)
CFG.register_opts(notifier_opts, group=notifier_group)

WARN = 'WARN'
INFO = 'INFO'
ERROR = 'ERROR'
CRITICAL = 'CRITICAL'
DEBUG = 'DEBUG'

log_levels = (DEBUG, WARN, INFO, ERROR, CRITICAL)


def notify(publisher_id, event_type, priority, payload):
    """
    Sends a notification using the specified driver

    Notify parameters:

    publisher_id - the source worker_type.host of the message
    event_type - the literal type of event (ex. Instance Creation)
    priority - patterned after the enumeration of Python logging levels in
               the set (DEBUG, WARN, INFO, ERROR, CRITICAL)
    payload - A python dictionary of attributes

    Outgoing message format includes the above parameters, and appends the
    following:

    message_id - a UUID representing the id for this notification
    timestamp - the GMT timestamp the notification was sent at

    The composite message will be constructed as a dictionary of the above
    attributes, which will then be sent via the transport mechanism defined
    by the driver.

    Message example:

    {'message_id': str(uuid.uuid4()),
     'publisher_id': 'compute.host1',
     'timestamp': '2012-03-26 00:00:00',
     'priority': 'WARN',
     'event_type': 'compute.create_instance',
     'payload': {'instance_id': 12, ... }}

    """
    if priority not in log_levels:
        raise ValueError(
                 _('%s not in valid priorities' % priority))

    msg = dict(message_id=str(uuid.uuid4()),
               publisher_id=publisher_id,
               event_type=event_type,
               priority=priority,
               payload=payload,
               timestamp=str(datetime.datetime.utcnow()))

    driver = _get_notifier_driver(CFG.notifier.driver)()
    driver.notify(msg)


class Notifier(object):
    def __init__(self, **kwargs):
        self.opts = kwargs

    def notify(self, msg):
        raise NotImplementedError()


class NoopNotifier(Notifier):
    def notify(self, msg):
        pass


class LoggingNotifier(Notifier):
    def __init__(self, **kwargs):
        super(LoggingNotifier, self).__init__(**kwargs)
        self._setup_logger()

    def _setup_logger(self):
        str2log_level = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARN': logging.WARN,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL}
        logging_level = str2log_level[CFG.notifier.level]
        self.logger = logging.getLogger('tempo.notifier.logging_notifier')
        self.logger.setLevel(logging_level)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging_level)
        self.logger.addHandler(stream_handler)

    def notify(self, msg):
        self.logger.debug(msg)


class RabbitNotifier(Notifier):
    def __init__(self, **kwargs):
        super(RabbitNotifier, self).__init__(**kwargs)
        self.connection = queue.get_connection()

    def notify(self, message):
        priority = message.get('priority', CFG.notifier.level)
        topic = "%s.%s" % (CFG.notifier.rabbit_topic, priority)
        queue = self.connection.SimpleQueue(topic)
        queue.put(message, serializer="json")
        queue.close()


def _get_notifier_driver(driver):
    if driver == "logging":
        return LoggingNotifier
    elif driver == "rabbit":
        return RabbitNotifier
    else:
        return NoopNotifier
