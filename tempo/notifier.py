import datetime
import logging
import uuid

from kombu.connection import BrokerConnection
from kombu.messaging import Exchange, Queue, Consumer, Producer

from tempo import flags


FLAGS = flags.FLAGS

flags.DEFINE_string('logging_notifier_level', 'DEBUG',
                    'logging level to use for LoggingNotifier')


WARN = 'WARN'
INFO = 'INFO'
ERROR = 'ERROR'
CRITICAL = 'CRITICAL'
DEBUG = 'DEBUG'

log_levels = (DEBUG, WARN, INFO, ERROR, CRITICAL)


class BadPriorityException(Exception):
    pass


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
     'timestamp': utils.utcnow(),
     'priority': 'WARN',
     'event_type': 'compute.create_instance',
     'payload': {'instance_id': 12, ... }}

    """
    if priority not in log_levels:
        raise BadPriorityException(
                 _('%s not in valid priorities' % priority))

    msg = dict(message_id=str(uuid.uuid4()),
               publisher_id=publisher_id,
               event_type=event_type,
               priority=priority,
               payload=payload,
               timestamp=str(datetime.datetime.utcnow()))

    __driver.notify(msg)


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
        logging_level_str = FLAGS.logging_notifier_level
        str2log_level = { 
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARN': logging.WARN,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL}
        logging_level = str2log_level[logging_level_str]
        self.logger = logging.getLogger('tempo.notifier.logging_notifier')
        self.logger.setLevel(logging_level)
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging_level)
        self.logger.addHandler(stream_handler)

    def notify(self, msg):
        self.logger.debug(msg)


class RabbitNotifier(Notifier):
    def __init__(self, **kwargs):
        super(LoggingNotifier, self).__init__(**kwargs)

    def notify(self, msg):
        self.logger.debug(msg)

__driver = None
def configure_notifier(driver, **kwargs):
    global __driver
    if driver == "logging":
        __driver = LoggingNotifier(**kwargs)
    else:
        __driver = NoopNotifier(**kwargs)
