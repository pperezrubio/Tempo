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
import datetime
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import exc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import literal_column

from tempo.db import models, migration

_ENGINE = None
_MAKER = None

BASE_ATTRS = set(['id', 'created_at', 'updated_at', 'deleted_at', 'deleted'])


class NotFoundException(Exception):
    pass


def configure_db(options):
    """
    Establish the database, create an engine if needed, and
    register the models.

    :param options: Mapping of configuration options
    """
    global _ENGINE
    if not _ENGINE:
        _ENGINE = create_engine(options.sql_connection,
                                pool_recycle=options.sql_idle_timeout)
        logger = logging.getLogger('sqlalchemy.engine')
        if options.debug:
            logger.setLevel(logging.DEBUG)
        elif options.verbose:
            logger.setLevel(logging.INFO)

        migration.db_sync(options)


def get_session(autocommit=True, expire_on_commit=False):
    """Helper method to grab session"""
    global _MAKER, _ENGINE
    if not _MAKER:
        assert _ENGINE
        _MAKER = sessionmaker(bind=_ENGINE,
                              autocommit=autocommit,
                              expire_on_commit=expire_on_commit)
    return _MAKER()


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
        raise NotFoundException("No task found with UUID %s" % task_uuid)


def task_create_or_update(task_uuid, values, session=None):
    if not session:
        session = get_session()

    try:
        task_ref = task_get(task_uuid, session=session)
    except NotFoundException, e:
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

    # Now update all existing items with new values, or create new param objects
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
