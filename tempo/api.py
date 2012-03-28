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
import flask
from flask import request

from tempo import actions
from tempo import config
from tempo import cron
from tempo import cronspec
from tempo import db
from tempo.openstack.common import cfg
from tempo.openstack.common import exception as common_exception

app = flask.Flask('tempo')

CFG = config.CFG

api_opts = [
    cfg.IntOpt('port',
               default=8080,
               help='The port to run the API server on'),
    cfg.BoolOpt('daemonized',
                default=False,
                help='Run the API as an eventlet WSGI app')
]

api_group = cfg.OptGroup(name='api', title='Tempo API options')
CFG.register_group(api_group)
CFG.register_opts(api_opts, group=api_group)


@app.route("/periodic_tasks")
def task_index():
    """Returns a list of all of the tasks"""
    task_dicts = [_make_task_dict(t) for t in db.task_get_all()]
    body = {'periodic_tasks': task_dicts}
    return _new_response(body)


@app.route("/periodic_tasks/<id>")
def task_show(id):
    """Returns a specific task record by id"""
    task = db.task_get(id)
    task_dict = _make_task_dict(task)
    body = {'periodic_task': task_dict}
    return _new_response(body)


@app.route("/periodic_tasks/<id>", methods=['PUT', 'POST'])
def task_create_or_update(id):
    """Creates or updates a new task record by id"""
    if request.content_type.lower() != 'application/json':
        return _error_response(412, "Invalid content type")

    try:
        req_body = flask.json.loads(request.data)
    except Exception as e:
        return _error_response(412, str(e))

    try:
        task_dict = _create_or_update_task(id, req_body)
    except common_exception.MissingArgumentError as e:
        return _error_response(412, str(e))
    except Exception as e:
        return _error_response(500, str(e))

    body = {'periodic_task': task_dict}
    res = _new_response(body)
    res.status_code = 202
    return res


@app.route("/periodic_tasks/<id>", methods=['DELETE'])
def task_delete(id):
    """Deletes a task record"""
    try:
        db.task_delete(id)
    except common_exception.NotFound as e:
        res = _error_response(404, str(e), log_error=False)
    except Exception as e:
        res = _error_response(500, str(e))
    else:
        res = app.make_response('')
        res.status_code = 204
        cron.update()

    return res


def _error_response(status_code, error_msg, log_error=True):
    res = app.make_response(error_msg)
    res.status_code = status_code
    if log_error:
        app.logger.critical(error_msg)
    return res


def _new_response(body):
    """Creates a Flask response and sets the content type"""
    res = app.make_response(flask.json.dumps(body))
    res.content_encoding = 'application/json'
    return res


def _create_or_update_task(id, body_dict):
    """Verifies the incoming keys are correct and creates the task record"""
    keys = ['action', 'instance_uuid', 'recurrence']
    for key in keys:
        if key not in body_dict:
            raise common_exception.MissingArgumentError(
                    "Missing key '%s' in body" % key)

    # Validate values
    cronspec.parse(body_dict['recurrence'])

    values = {
        'deleted': False,
        'uuid': id,
        'instance_uuid': body_dict['instance_uuid'],
        'cron_schedule': body_dict['recurrence'],
        'action': body_dict['action']
    }

    task = db.task_create_or_update(id, values)

    params = body_dict.get('params')
    if params:
        delete = params.pop('__delete', False)
        db.task_parameter_update(id, params, delete=delete)

    cron.update()
    return _make_task_dict(task)


def _make_task_dict(task):
    """
    Create a dict representation of an image which we can use to
    serialize the task.
    """
    def _format_date(date):
        return date.strftime('%Y-%m-%d %H:%M:%S') if date else date

    return {
        'id': task.id,
        'created_at': _format_date(task.created_at),
        'updated_at': _format_date(task.updated_at),
        'deleted_at': _format_date(task.deleted_at),
        'deleted': task.deleted,
        'uuid': task.uuid,
        'instance_uuid': task.instance_uuid,
        'recurrence': task.cron_schedule,
        'action': task.action,
        'params': db.task_parameter_get_all_by_task_uuid(task.uuid)
    }


def start():
    """Starts up the flask API worker"""
    if CFG.api.daemonized:
        # TODO(mdietz): there's a cleaner way to do this, but this works well
        # as a way of backgrounding the server for now
        import daemon
        from eventlet import wsgi
        import eventlet
        with daemon.DaemonContext():
            wsgi.server(eventlet.listen(('', CFG.api.port)), app)
    else:
        app.run(port=CFG.api.port, debug=CFG.debug)
