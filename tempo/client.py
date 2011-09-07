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
    def _task_create_update(self, req, id, task, instance_uuid, recurrence):
        """Create or update an existing task."""

        # Build the task object we're going to send
        obj = dict(task=task, instance_uuid=instance_uuid,
                   recurrence=recurrence)

        # Attach it to the request
        self._attach_obj(req, obj)

        # Send the request
        resp = req.send()

        # Return the result
        return resp.obj[resource_name]

    def task_create(self, task, instance_uuid, recurrence):
        """Create a task."""
        id = str(uuid.uuid4())
        return self._task_create_update(
            id, task, instance_uuid, recurrence)

    def task_update(self, id, task, instance_uuid, recurrence):
        """Update an existing task."""
        return self._task_create_update(
            id, task, instance_uuid, recurrence)

    @requiem.restmethod('DELETE', resource)
    def task_delete(self, req, id):
        """Delete a task."""

        # Send the request and ignore the return; Requiem raises an
        # exception if we get an error, and success returns a 204
        req.send()
