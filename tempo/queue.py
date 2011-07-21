from kombu.connection import BrokerConnection

from tempo import flags


FLAGS = flags.FLAGS

_CONNECTION = None

def get_connection():
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = BrokerConnection(
                hostname=FLAGS.rabbit_host,
                userid=FLAGS.rabbit_userid,
                password=FLAGS.rabbit_password,
                virtual_host=FLAGS.rabbit_virtual_host,
                ssl=FLAGS.rabbit_use_ssl)

    return _CONNECTION
