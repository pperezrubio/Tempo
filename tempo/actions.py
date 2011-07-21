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

actions_by_name = {}
actions_by_id = {}

logger = logging.getLogger('tempo.actions')


def register_action(c):
    i = c()
    actions_by_name[i.name] = i
    actions_by_id[i.id] = i

    return c


@register_action
class Snapshot(object):
    name = 'snapshot'
    id = 1

    def command(self, task):
        task_uuid = task.uuid
        snapshot_name = "snapshot"
        cmd = "tempo-cron-snapshot %(task_uuid)s %(snapshot_name)s" % locals()
        logger.debug("cmd => %s" % cmd)
        return cmd
