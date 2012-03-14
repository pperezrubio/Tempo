# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import optparse
import subprocess

import kombu

import tempo.actions
import tempo.db
import tempo.flags
import tempo.notifier
import tempo.queue


FLAGS = tempo.flags.FLAGS


class ExecutionFailed(Exception):
    def __init__(self, returncode, stdout, stderr, max_exc_stream_len=64):
        self.returncode = returncode
        self.stdout = stdout[:max_exc_stream_len]
        self.stderr = stderr[:max_exc_stream_len]
        self.max_exc_stream_len = max_exc_stream_len

    def __repr__(self):
        return "<ExecutionFailed returncode=%d stdout='%r' stderr='%r'>" % (
            self.returncode, self.stdout, self.stderr)

    __str__ = __repr__


def execute_cmd(cmd, ok_exit_codes=None):
    if ok_exit_codes is None:
        ok_exit_codes = [0]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode not in ok_exit_codes:
        raise ExecutionFailed(proc.returncode, stdout, stderr)

    return proc.returncode, stdout, stderr


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


class QueueWorker(object):
    def __init__(self, exchange, queue, key, logger_name):
        self.exchange = exchange
        self.queue = queue
        self.key = key
        self.logger_name = logger_name

    def configure(self):
        self.logger = logging.getLogger(self.logger_name)
        parser = make_options_parser()
        add_db_options(parser)
        opts, args = parser.parse_args()
        configure_logging(self.logger, opts)
        tempo.db.configure_db(opts)

    def perform_task(self, task):
        def _notify(event_type, exception=None):
            payload = {'task_uuid': task_uuid}
            if exception is not None:
                payload['exception'] = exception

            publisher_id = FLAGS.host
            priority = tempo.notifier.DEBUG
            tempo.notifier.notify(publisher_id, event_type, priority, payload)

        action = task.action
        task_uuid = task.uuid
        try:
            func = getattr(tempo.actions, action)
        except AttributeError:
            self.logger.error("unrecognized action '%(action)s' for task task"
                              " '%(task_uuid)s'" % locals())
            return

        self.logger.debug("task '%(task_uuid)s' started: '%(action)s'" %
                          locals())

        _notify('Started Task')

        try:
            func(task)
        except Exception as e:
            self.logger.error(
                "task '%(task_uuid)s' errored: %(e)s" % locals())

            _notify('Errored Task', exception=e)
        else:
            self.logger.debug(
                "task '%(task_uuid)s' finished: returned successfully" %
                locals())

            _notify('Finished Task')

    def process_message(self, body, message):
        message.ack()

        task_uuid = body['task_uuid']

        try:
            task = tempo.db.task_get(task_uuid)
        except tempo.db.api.NotFoundException as e:
            self.logger.error("Task '%(task_uuid)s' not found" % locals())
            return

        self.perform_task(task)

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
