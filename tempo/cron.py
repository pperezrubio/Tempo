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

from tempo import db
from tempo.openstack.common import exception as common_exception
from tempo.openstack.common import utils as common_utils

logger = logging.getLogger('tempo.cron')


def crontab():
    DAY_OF_MONTH = "*"
    MONTH = "*"

    lines = []
    for task in db.task_get_all():
        minute, hour, day_of_week = task.cron_schedule.split(' ')
        schedule = ' '.join([minute, hour, DAY_OF_MONTH, MONTH, day_of_week])
        line = '%s tempo-enqueue %s' % (schedule, task.uuid)
        lines.append(line)

    # Trailing new line is required by cron format
    lines.append('')
    return '\n'.join(lines)


def update():
    """Updates the crontab based on the state of the DB."""
    try:
        common_utils.execute('crontab', '-', process_input=crontab())
    except common_exception.ProcessExecutionError as e:
        logger.exception(e)
