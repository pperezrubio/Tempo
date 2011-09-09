import logging
import optparse
import subprocess

import kombu

import tempo.db
import tempo.flags
import tempo.notifier
import tempo.queue


FLAGS = tempo.flags.FLAGS


def publish_message(topic, message):
    connection = tempo.queue.get_connection()
    queue = connection.SimpleQueue(topic)
    queue.put(message, serializer="json")
    queue.close()


def make_options_parser():
    parser = optparse.OptionParser()
    parser.add_option('--debug', dest='debug', action='store_true',
                      help='Enable debug mode', default=False)
    parser.add_option('--verbose', dest='verbose', action='store_true',
                      help='Enable verbose logging', default=False)
    return parser


def add_db_options(parser):
    parser.add_option('--sql_connection', dest='sql_connection',
                      help='SQL Connection', default='sqlite:///tempo.sqlite')
    parser.add_option('--sql_idle_timeout', dest='sql_idle_timeout',
                      help='SQL Idle Timeout', type='int', default=3600)


def configure_logging(logger, opts):
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()

    if opts.debug:
        level = logging.DEBUG
    elif opts.verbose:
        level = logging.INFO
    else:
        level = logging.WARN

    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)
    return level


def execute_cmd(cmd):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return_code = proc.returncode
    return return_code, stdout, stderr


class QueueWorker(object):
    def __init__(self, exchange, queue, key, logger_name):
        self.exchange = exchange
        self.queue = queue
        self.key = key
        self.logger_name = logger_name

    def make_command(self, task, body, message):
        """Override this to change worker behavior"""
        raise NotImplementedError

    def configure(self):
        self.logger = logging.getLogger(self.logger_name)
        parser = make_options_parser()
        add_db_options(parser)
        opts, args = parser.parse_args()
        configure_logging(self.logger, opts)
        tempo.db.configure_db(opts)

    def perform_task(self, task_uuid, cmd):
        logger = self.logger

        def _notify(event_type, return_code=None):
            payload = {'task_uuid': task_uuid}
            if return_code is not None:
                payload['return_code'] = return_code

            publisher_id = FLAGS.host
            priority = tempo.notifier.DEBUG
            tempo.notifier.notify(publisher_id, event_type, priority, payload)

        logger.debug("task '%(task_uuid)s' started: '%(cmd)s'" % locals())
        _notify('Started Task')

        return_code, stdout, stderr = tempo.command.execute_cmd(cmd)

        if return_code == 0:
            logger.debug("task '%(task_uuid)s' finished: returned successfully"
                         % locals())
            _notify('Finished Task')
        else:
            logger.error("task '%(task_uuid)s' errored: ret=%(return_code)s"
                         % locals())
            _notify('Errored Task', return_code=return_code)

    def process_message(self, body, message):
        message.ack()

        task_uuid = body['task_uuid']

        try:
            task = tempo.db.task_get(task_uuid)
        except tempo.db.api.NotFoundException as e:
            logger.error("Task '%(task_uuid)s' not found" % locals())
            return

        cmd = self.make_command(task, body, message)
        self.perform_task(task_uuid, cmd)

    def run(self):
        tempo_exchange = kombu.Exchange(self.exchange, 'direct', durable=True)
        tempo_queue = kombu.Queue(self.queue, exchange=tempo_exchange,
                                  key=self.key)

        connection = tempo.queue.get_connection()
        channel = connection.channel()

        consumer = kombu.Consumer(channel, tempo_queue)
        consumer.register_callback(self.process_message)
        consumer.consume()

        while True:
            connection.drain_events()
