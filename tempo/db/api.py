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
import datetime
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import literal_column

from tempo import config
from tempo.db import models
from tempo.db import migration
from tempo.openstack.common import cfg
from tempo.openstack.common import exception as common_exception

CFG = config.CFG

db_opts = [
    # TODO(sirp): make sql_connection match Nova exactly
    cfg.StrOpt('sql_connection',
               default='sqlite:///tempo.sqlite',
               help='The SQLAlchemy connection string used to connect to the '
                    'database'),
    cfg.IntOpt('sql_idle_timeout',
               default=3600,
               help='timeout before idle sql connections are reaped')
]

db_group = cfg.OptGroup(name='db', title='Database options')
CFG.register_group(db_group)
CFG.register_opts(db_opts, group=db_group)

_ENGINE = None


def get_engine():
    """
    Establish the database, create an engine if needed, and
    register the models.

    :param options: Mapping of configuration options
    """
    global _ENGINE
    if not _ENGINE:
        _ENGINE = create_engine(CFG.db.sql_connection,
                                pool_recycle=CFG.db.sql_idle_timeout)
    return _ENGINE


_MAKER = None


def get_session(autocommit=True, expire_on_commit=False):
    """Helper method to grab session"""
    global _MAKER
    if not _MAKER:
        _MAKER = sessionmaker(bind=get_engine(),
                              autocommit=autocommit,
                              expire_on_commit=expire_on_commit)
    session = _MAKER()
    return session


def task_get_all(session=None):
    if not session:
        session = get_session()

    return session.query(models.Task).\
                   filter_by(deleted=False).\
                   all()


def task_get(task_uuid, session=None):
    if not session:
        session = get_session()

    try:
        return session.query(models.Task).\
                       filter_by(uuid=task_uuid).\
                       filter_by(deleted=False).\
                       one()
    except exc.NoResultFound:
        raise common_exception.NotFound(
                "No task found with UUID %s" % task_uuid)


def task_create_or_update(task_uuid, values, session=None):
    if not session:
        session = get_session()

    try:
        task_ref = task_get(task_uuid, session=session)
    except common_exception.NotFound:
        task_ref = models.Task()

    task_ref.update(values)
    task_ref.save(session=session)
    return task_ref


def task_delete(task_uuid, session=None):
    if not session:
        session = get_session()

    with session.begin():
        task_ref = task_get(task_uuid, session=session)
        task_ref.delete(session=session)

        orig_params = task_parameter_get_all_by_task_uuid(task_uuid)
        for key in orig_params:
            task_parameter_delete(task_uuid, key, session=session)


def task_parameter_get_all_by_task_uuid(task_uuid, session=None):
    if not session:
        session = get_session()

    rows = session.query(models.TaskParameter).\
                   filter_by(task_uuid=task_uuid).\
                   filter_by(deleted=False).\
                   all()

    params = {}
    for row in rows:
        params[row['key']] = row['value']

    return params


def task_parameter_delete(task_uuid, key, session=None):
    if not session:
        session = get_session()

    session.query(models.TaskParameter).\
            filter_by(task_uuid=task_uuid).\
            filter_by(deleted=False).\
            filter_by(key=key).\
            update({'deleted': True,
                    'deleted_at': datetime.datetime.utcnow(),
                    'updated_at': literal_column('updated_at')})


def _task_parameter_get_item(task_uuid, key, session=None):
    if not session:
        session = get_session()

    return session.query(models.TaskParameter).\
            filter_by(task_uuid=task_uuid).\
            filter_by(deleted=False).\
            filter_by(key=key).\
            first()


def task_parameter_update(task_uuid, params, delete=False, session=None):
    if not session:
        session = get_session()

    # Set existing parameters to deleted if delete argument is True
    orig_params = task_parameter_get_all_by_task_uuid(task_uuid)

    if delete:
        for key in orig_params:
            if key not in params:
                task_parameter_delete(task_uuid, key, session=session)

    # Now update all existing items with new values, or create new param
    # objects
    for key, value in params.iteritems():
        if key in orig_params:
            param_ref = _task_parameter_get_item(
                    task_uuid, key, session=session)
            if param_ref is None:
                continue
        else:
            param_ref = models.TaskParameter()
            param_ref.key = key
            param_ref.task_uuid = task_uuid

        param_ref.value = value
        param_ref.save(session=session)

    return params
