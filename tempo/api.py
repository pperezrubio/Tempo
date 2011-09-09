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


import flask
from flask import request
import subprocess

from tempo import db, actions, cronspec


app = flask.Flask('Tempo')
resource_name = 'periodic_task'
resources_name = '%ss' % resource_name
resource = "/%s/<id>" % resources_name


@app.route("/%s" % resources_name)
def task_index():
    """Returns a list of all of the tasks"""
    return _new_response({resources_name: [_make_task_dict(t)
                          for t in db.task_get_all()]})


@app.route(resource)
def task_show(id):
    """Returns a specific task record by id"""
    return _new_response({resource_name: _make_task_dict(db.task_get(id))})


@app.route(resource, methods=['PUT', 'POST'])
def task_create_or_update(id):
    """Creates or updates a new task record by id"""
    res = None
    try:
        if request.content_type.lower() != 'application/json':
            raise Exception("Invalid content type")
        body = flask.json.loads(request.data)
        res = _new_response({resource_name: _create_or_update_task(id, body)})
        res.status_code = 202
    except Exception, e:
        app.logger.error('Exception in create_or_update \n\n%s' % e)
        res = app.make_response('There was an error processing your request\n')
        res.content_encoding = 'text/plain'
        res.status_code = 412
    return res


@app.route(resource, methods=['DELETE'])
def task_delete(id):
    """Deletes a task record"""
    try:
        db.task_delete(id)
    except db.NotFoundException, e:
        return _not_found(e)
    except Exception, e:
        return _log_and_fail(e)
    _update_crontab()
    res = app.make_response('')
    res.status_code = 204
    return res


@app.errorhandler(404)
def _not_found(error):
    res = app.make_response(str(error))
    res.status_code = 404
    return res


def _log_and_fail(error):
    """Funnel method for logging all unknown exceptions"""
    res = app.make_response(str(error))
    res.status_code = 500
    app.logger.critical(error)
    return res


def _new_response(body):
    """Creates a Flask response and sets the content type"""
    res = app.make_response(flask.json.dumps(body))
    res.content_encoding = 'application/json'
    return res


def _create_or_update_task(id, body_dict):
    """Verifies the incoming keys are correct and creates the task record"""
    keys = ['task', 'instance_uuid', 'recurrence']
    for key in keys:
        if key not in body_dict:
            raise Exception("Missing key %s in body" % key)

    # Validate values
    cronspec.parse(body_dict['recurrence'])

    values = {
        'deleted': False,
        'uuid': id,
        'instance_uuid': body_dict['instance_uuid'],
        'cron_schedule': body_dict['recurrence'],
        'action_id': actions.actions_by_name[body_dict['task']].id,
    }
    task_dict = _make_task_dict(db.task_create_or_update(id, values))
    _update_crontab()
    return task_dict


def _make_task_dict(task):
    """
    Create a dict representation of an image which we can use to
    serialize the task.
    """
    task_dict = {
        'id': task.id,
        'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': task.updated_at and
                      task.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        'deleted_at': task.deleted_at and
                      task.deleted_at.strftime('%Y-%m-%d %H:%M:%S'),
        'deleted': task.deleted,
        'uuid': task.uuid,
        'instance_uuid': task.instance_uuid,
        'recurrence': task.cron_schedule,
        'task': actions.actions_by_id[task.action_id].name,
    }
    return task_dict


def _make_crontab_line_for_task(task):
    action = actions.actions_by_id[task.action_id]
    minute, hour, day_of_week = task.cron_schedule.split(' ')
    day_of_month = "*"
    month = "*"
    schedule = ' '.join([minute, hour, day_of_month, month, day_of_week])
    line = '%s %s' % (schedule, action.command(task))
    return line


def _write_cron_data(cron_data):
    PIPE = subprocess.PIPE
    p = subprocess.Popen(
        ['crontab', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate(cron_data)
    if p.returncode:
        app.logger.error('Error running crontab update: %s' % p.returncode)
    if stdout:
        app.logger.error('Output from crontab update:\n\n%s' % stdout)
    if stderr:
        app.logger.error('Error from crontab update:\n\n%s' % stderr)


def _update_crontab():
    lines = [_make_crontab_line_for_task(task) for task in db.task_get_all()]
    # NOTE(sirp): cron requires a trailing newline on the final entry,
    # otherwise it won't install the new cron entries
    cron_data = '\n'.join(lines) + '\n'
    _write_cron_data(cron_data)


def start(*args, **kwargs):
    """Starts up the flask API worker"""
    app.run(*args, **kwargs)
