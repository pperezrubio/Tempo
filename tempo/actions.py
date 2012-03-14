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
import tempo.command


def snapshot(task):
    snapshot_name = 'snapshot'
    tempo.command.execute_cmd(
        ['nova', 'image-create', task.instance_uuid, snapshot_name])


def _backup(task, backup_type):
    backup_name = backup_type
    rotation = 7
    tempo.command.execute_cmd(
        ['nova', 'backup', task.instance_uuid, backup_name, backup_type,
         str(rotation)])


def daily_backup(task):
    _backup(task, 'daily')


def weekly_backup(task):
    _backup(task, 'weekly')
