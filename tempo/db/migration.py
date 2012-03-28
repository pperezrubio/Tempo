# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2011 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import logging
import os

from tempo import config

from migrate.versioning import api as versioning_api

# See LP bug #719834. sqlalchemy-migrate changed location of
# exceptions.py after 0.6.0.
try:
    from migrate.versioning import exceptions as versioning_exceptions
except ImportError:
    from migrate import exceptions as versioning_exceptions

logger = logging.getLogger('tempo.db.migration')

CFG = config.CFG


class DatabaseMigrationError(Exception):
    pass


def db_version():
    """Return the database's current migration number."""
    repo_path = get_migrate_repo_path()
    sql_connection = CFG.db.sql_connection
    try:
        return versioning_api.db_version(sql_connection, repo_path)
    except versioning_exceptions.DatabaseNotControlledError, e:
        msg = ("database '%(sql_connection)s' is not under migration control"
               % locals())
        raise DatabaseMigrationError(msg)


def upgrade(version=None):
    """Upgrade the database's current migration level."""
    db_version()  # Ensure db is under migration control
    repo_path = get_migrate_repo_path()
    sql_connection = CFG.db.sql_connection
    version_str = version or 'latest'
    logger.info("Upgrading %(sql_connection)s to version %(version_str)s" %
                locals())
    return versioning_api.upgrade(sql_connection, repo_path, version)


def downgrade(version):
    """Downgrade the database's current migration level."""
    db_version()  # Ensure db is under migration control
    repo_path = get_migrate_repo_path()
    sql_connection = CFG.db.sql_connection
    logger.info("Downgrading %(sql_connection)s to version %(version)s" %
                locals())
    return versioning_api.downgrade(sql_connection, repo_path, version)


def version_control():
    """Place a database under migration control."""
    sql_connection = CFG.db.sql_connection
    try:
        versioning_api.version_control(
                CFG.sql_connection, get_migrate_repo_path())
    except versioning_exceptions.DatabaseAlreadyControlledError, e:
        msg = ("database '%(sql_connection)s' is already under migration "
               "control" % locals())
        raise DatabaseMigrationError(msg)


def db_sync(version=None):
    """Place a database under migration control and perform an upgrade."""
    try:
        versioning_api.version_control(
            CFG.db.sql_connection, get_migrate_repo_path())
    except versioning_exceptions.DatabaseAlreadyControlledError, e:
        pass

    upgrade(version=version)


def get_migrate_repo_path():
    """Get the path for the migrate repository."""
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                        'migrate_repo')
    assert os.path.exists(path)
    return path
