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
from kombu.connection import BrokerConnection

from tempo import config
from tempo.openstack.common import cfg

CFG = config.CFG

rabbit_opts = [
    cfg.StrOpt('host',
               default='localhost',
               help='Rabbit host'),
    cfg.IntOpt('port',
               default=5672,
               help='Rabbit port'),
    cfg.BoolOpt('use_ssl',
                default=False,
                help='Connect to Rabbit over SSL'),
    cfg.StrOpt('userid',
               default='guest',
               help='Rabbit user ID'),
    cfg.StrOpt('password',
               default='guest',
               help='Rabbit password'),
    cfg.StrOpt('virtual_host',
               default='/',
               help='Rabbit virtual host')
]

rabbit_group = cfg.OptGroup(name='rabbit', title='RabbitMQ options')
CFG.register_group(rabbit_group)
CFG.register_opts(rabbit_opts, group=rabbit_group)

_CONNECTION = None


def get_connection():
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = BrokerConnection(
                hostname=CFG.rabbit.host,
                port=CFG.rabbit.port,
                userid=CFG.rabbit.userid,
                password=CFG.rabbit.password,
                virtual_host=CFG.rabbit.virtual_host,
                ssl=CFG.rabbit.use_ssl)

    return _CONNECTION


def publish_message(topic, message):
    connection = get_connection()
    queue = connection.SimpleQueue(topic)
    try:
        queue.put(message, serializer="json")
    finally:
        queue.close()
