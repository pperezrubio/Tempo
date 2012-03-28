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

"""Interface with a Tempo server"""
import uuid

import requiem
from requiem import jsclient


# Parameterize the resource names
resource_name = 'periodic_task'
resources_name = '%ss' % resource_name
resource = "/%s/{id}" % resources_name


class TempoClient(jsclient.JSONClient):
    """A client class for accessing the Tempo service."""

    @requiem.restmethod('GET', "/%s" % resources_name)
    def task_get_all(self, req):
        """Retrieve a list of all existing tasks."""

        # Send the request
        resp = req.send()

        # Return the result
        return resp.obj[resources_name]

    @requiem.restmethod('GET', resource)
    def task_get(self, req, id):
        """Retrieve a task by its ID."""

        # Send the request
        resp = req.send()

        # Return the result
        return resp.obj[resource_name]

    @requiem.restmethod('PUT', resource)
    def _task_create_update(self, req, id, action, instance_uuid, recurrence,
                            params, clear_params):
        """Create or update an existing task.

        :param action: String representing which action to take (
                       e.g. 'snapshot' or 'daily_backup')

        :param instance_uuid: Instance identiier

        :param recurrence: String like "* * *" representing a task recurrence

        :param params: Dict of task parameters to set.

        :param clear_params: True means task parameters will be cleared before
                             being set to the new value.
        """
        if params is None:
            params = {}
        else:
            params['__delete'] = clear_params

        # Build the task object we're going to send
        obj = dict(action=action,
                   instance_uuid=instance_uuid,
                   recurrence=recurrence,
                   params=params)

        # Attach it to the request
        self._attach_obj(req, obj)

        # Send the request
        resp = req.send()

        # Return the result
        return resp.obj[resource_name]

    def task_create(self, action, instance_uuid, recurrence, params=None,
                    clear_params=False):
        """Create a task."""
        id = str(uuid.uuid4())
        return self._task_create_update(
            id, action, instance_uuid, recurrence, params, clear_params)

    def task_update(self, id, action, instance_uuid, recurrence, params=None,
                    clear_params=False):
        """Update an existing task."""
        return self._task_create_update(
            id, action, instance_uuid, recurrence, params, clear_params)

    @requiem.restmethod('DELETE', resource)
    def task_delete(self, req, id):
        """Delete a task."""

        # Send the request and ignore the return; Requiem raises an
        # exception if we get an error, and success returns a 204
        req.send()
