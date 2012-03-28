# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Rackspace
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

import kombu

from tempo import actions
from tempo import config
from tempo import db
from tempo import notifier
from tempo import queue as tempo_queue
from tempo.openstack.common import cfg
from tempo.openstack.common import exception as common_exception

CFG = config.CFG

logger = logging.getLogger('tempo.worker')

worker_opts = [
    cfg.BoolOpt('daemonized',
                default=False,
                help='Run worker as a daemon'),
    cfg.StrOpt('publisher_id',
               default='host',
               help='Where the notification came from')
]

worker_group = cfg.OptGroup(name='worker', title='Worker options')
CFG.register_group(worker_group)
CFG.register_opts(worker_opts, group=worker_group)


def _perform_task(task):
    def _notify(event_type, exception=None):
        payload = {'task_uuid': task_uuid}
        if exception is not None:
            payload['exception'] = exception

        publisher_id = CFG.worker.publisher_id
        priority = notifier.DEBUG
        notifier.notify(publisher_id, event_type, priority, payload)

    action = task.action
    task_uuid = task.uuid
    try:
        func = getattr(actions, action)
    except AttributeError:
        logger.error("unrecognized action '%(action)s' for task task"
                     " '%(task_uuid)s'" % locals())
        return

    logger.debug("task '%(task_uuid)s' started: '%(action)s'" % locals())

    _notify('Started Task')

    try:
        func(task)
    except Exception as e:
        logger.error("task '%(task_uuid)s' errored: %(e)s" % locals())
        _notify('Errored Task', exception=e)
    else:
        logger.debug("task '%(task_uuid)s' finished: returned successfully" %
                     locals())
        _notify('Finished Task')


def _process_message(body, message):
    message.ack()

    task_uuid = body['task_uuid']

    try:
        task = db.task_get(task_uuid)
    except common_exception.NotFound:
        logger.error("Task '%(task_uuid)s' not found" % locals())
        return

    _perform_task(task)


def _consume_messages(exchange, queue, key):
    kombu_xchg = kombu.Exchange(exchange, 'direct', durable=True)
    kombu_queue = kombu.Queue(queue, exchange=kombu_xchg, key=key)

    connection = tempo_queue.get_connection()

    consumer = kombu.Consumer(connection.channel(), kombu_queue)
    consumer.register_callback(_process_message)
    consumer.consume()

    while True:
        connection.drain_events()


def consume_messages(exchange, queue, key):
    if CFG.worker.daemonized:
        # TODO(mdietz): there's a cleaner way to do this, but this works well
        # as a way of backgrounding the server for now
        import daemon
        with daemon.DaemonContext():
            _consume_messages(exchange, queue, key)
    else:
        _consume_messages(exchange, queue, key)
