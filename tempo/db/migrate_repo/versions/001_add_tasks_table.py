# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

from sqlalchemy.schema import (Column, MetaData, Table)

from tempo.db.migrate_repo.schema import (
    Boolean, DateTime, Integer, String, Text, create_tables, drop_tables)


meta = MetaData()

tasks = Table('tasks', meta,
    Column('id', Integer(), primary_key=True, nullable=False),
    Column('uuid', String(36)),
    Column('instance_uuid', String(36)),
    Column('cron_schedule', String(255)),
    Column('action_id', Integer()),
    Column('created_at', DateTime(), nullable=False),
    Column('updated_at', DateTime()),
    Column('deleted_at', DateTime()),
    Column('deleted', Boolean(), nullable=False, default=False,
           index=True))


def upgrade(migrate_engine):
    meta.bind = migrate_engine
    create_tables([tasks])


def downgrade(migrate_engine):
    meta.bind = migrate_engine
    drop_tables([tasks])
