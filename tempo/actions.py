# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
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

from tempo import db
from tempo.openstack.common import utils as common_utils


logger = logging.getLogger('tempo.actions')


def snapshot(task):
    snapshot_name = 'snapshot'
    common_utils.execute(
        'nova', 'image-create', task.instance_uuid, snapshot_name)


def _backup(task, backup_type):
    task_uuid = task.uuid
    params = db.task_parameter_get_all_by_task_uuid(task_uuid)
    rotation = params.get('rotation', '0')

    try:
        rotation = int(rotation)
    except ValueError:
        logger.error("Invalid rotation '%(rotation)s' for task"
                     " '%(task_uuid)s'" % locals())
        rotation = 0

    backup_name = backup_type
    common_utils.execute(
        'nova', 'backup', task.instance_uuid, backup_name, backup_type,
        str(rotation))


def daily_backup(task):
    _backup(task, 'daily')


def weekly_backup(task):
    _backup(task, 'weekly')
