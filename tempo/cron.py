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
import os

from tempo import config
from tempo import db
from tempo.openstack.common import cfg
from tempo.openstack.common import exception as common_exception
from tempo.openstack.common import utils as common_utils

logger = logging.getLogger('tempo.cron')

CFG = config.CFG

cron_opts = [
    cfg.StrOpt('schedule_override',
               default=None,
               help='Cron formatted schedule to use for all tasks.'
                    ' For debugging purposes.'),
    cfg.StrOpt('tempo_enqueue_path',
               default='/usr/local/bin',
               help='Path to tempo-enqueue.')
]

cron_group = cfg.OptGroup(name='cron', title='Tempo Cron options')
CFG.register_group(cron_group)
CFG.register_opts(cron_opts, group=cron_group)

def crontab():
    DAY_OF_MONTH = "*"
    MONTH = "*"

    lines = []
    for task in db.task_get_all():

        if CFG.cron.schedule_override:
            schedule = CFG.cron.schedule_override
        else:
            minute, hour, day_of_week = task.cron_schedule.split(' ')
            schedule = ' '.join([minute, hour, DAY_OF_MONTH, MONTH, day_of_week])

        bin_path = os.path.join(CFG.cron.tempo_enqueue_path, 'tempo-enqueue')
        lines.append(' '.join([schedule, bin_path, task.uuid]))

    # Trailing new line is required by cron format
    lines.append('')
    return '\n'.join(lines)


def update():
    """Updates the crontab based on the state of the DB."""
    try:
        common_utils.execute('crontab', '-', process_input=crontab())
    except common_exception.ProcessExecutionError as e:
        logger.exception(e)
