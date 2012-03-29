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

import json
import unittest

import stubout

from tempo import api
from tempo import cron
from tempo import db
from tempo.openstack.common import utils as common_utils
from tempo.openstack.common import exception as common_exception

TEST_UUID = '00010203-0405-0607-0809-0a0b0c0d0e0f'


class APITest(unittest.TestCase):
    def setUp(self):
        self.app = api.app.test_client()
        self.stubs = stubout.StubOutForTesting()

    def tearDown(self):
        self.stubs.UnsetAll()

    def test_bad_route(self):
        res = self.app.get('/foo')
        self.assertEqual(res.status_code, 404)

    def test_index_no_items(self):
        def stubbed_index():
            return []

        self.stubs.Set(db, 'task_get_all', stubbed_index)
        res = self.app.get('/periodic_tasks')
        body = json.loads(res.data)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(body['periodic_tasks']), 0)

    def test_index_with_items(self):
        def stubbed_index():
            elements = [1, 2, 3, 4, 5]
            return elements

        self.stubs.Set(db, 'task_get_all', stubbed_index)
        self.stubs.Set(api, '_make_task_dict', lambda t: t)
        res = self.app.get('/periodic_tasks')
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.data)
        self.assertEqual(len(body['periodic_tasks']), 5)

    def test_show_item(self):
        def stubbed_show(id):
            return 'foo'

        self.stubs.Set(db, 'task_get', stubbed_show)
        self.stubs.Set(api, '_make_task_dict', lambda t: t)
        res = self.app.get('/periodic_tasks/%s' % TEST_UUID)
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.data)
        self.assertEqual(body['periodic_task'], 'foo')

    def test_create_item(self):
        self.called = False

        def stubbed_create(id, values):
            self.called = True
            return values

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        self.stubs.Set(api, '_make_task_dict', lambda t: t)
        self.stubs.Set(cron, 'update', lambda: None)
        body = {'action': 'snapshot', 'instance_uuid': 'abcdef',
                'recurrence': '0 0 0', 'rotation': 3}
        res = self.app.post('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(self.called, True)
        self.assertEqual(res.status_code, 202)

    def test_create_item_with_put(self):
        self.called = False

        def stubbed_create(id, values):
            self.called = True
            return values

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        self.stubs.Set(api, '_make_task_dict', lambda t: t)
        self.stubs.Set(cron, 'update', lambda: None)
        body = {'action': 'snapshot', 'instance_uuid': 'abcdef',
                'recurrence': '0 0 0'}
        res = self.app.put('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(self.called, True)
        self.assertEqual(res.status_code, 202)

    def test_create_item_no_task_fails(self):
        self.called = False

        def stubbed_create(id, values):
            self.called = True
            return values

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        body = {'instance_uuid': 'abcdef', 'recurrence': '0 0 0'}
        res = self.app.put('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(self.called, False)
        self.assertEqual(res.status_code, 412)

    def test_create_item_no_uuid_fails(self):
        self.called = False

        def stubbed_create(id, values):
            self.called = True
            return values

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        body = {'action': 'snapshot', 'recurrence': '0 0 0'}
        res = self.app.put('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(self.called, False)
        self.assertEqual(res.status_code, 412)

    def test_create_item_no_recurrence_fails(self):
        self.called = False

        def stubbed_create(id, values):
            self.called = True
            return values

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        body = {'action': 'snapshot', 'instance_uuid': 'abcdef'}
        res = self.app.put('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(self.called, False)
        self.assertEqual(res.status_code, 412)

    def test_delete_item(self):
        self.called = False

        def stubbed_delete(id):
            self.called = True

        self.stubs.Set(db, 'task_delete', stubbed_delete)
        self.stubs.Set(cron, 'update', lambda: None)
        res = self.app.delete('/periodic_tasks/%s' % TEST_UUID)
        self.assertEqual(self.called, True)
        self.assertEqual(res.status_code, 204)

    def test_delete_item_not_exist_fails(self):
        def stubbed_delete(id):
            raise common_exception.NotFound()

        self.stubs.Set(db, 'task_delete', stubbed_delete)
        res = self.app.delete('/periodic_tasks/%s' % TEST_UUID)
        self.assertEqual(res.status_code, 404)

    def test_delete_item_random_breakage_fails(self):
        def stubbed_delete(id):
            raise Exception("KABOOM")

        self.stubs.Set(db, 'task_delete', stubbed_delete)
        res = self.app.delete('/periodic_tasks/%s' % TEST_UUID)
        self.assertEqual(res.status_code, 500)


class TestCronOutput(APITest):
    """
    Recurrence is specified as an abbreviated crontab line w/ 3 parts:

        1. minute
        2. hour
        3. day of week

    This test ensures that the abbreviated cron spec is generates a valid
    crontab entry.
    """
    def setUp(self):
        super(TestCronOutput, self).setUp()
        self.stub_rvs = {}

        class FakeModel(object):
            def __init__(self, values):
                self.__dict__.update(values)

        def stubbed_create(id, values):
            self.stub_rvs['create'] = FakeModel(values)
            return values

        def stubbed_get_all():
            task = self.stub_rvs['create']
            return [task]

        def stubbed_execute(*cmd, **kwargs):
            self.stub_rvs['cmd'] = list(cmd)
            self.stub_rvs['stdin'] = kwargs.get('process_input')
            return 0, '', ''

        self.stubs.Set(db, 'task_create_or_update', stubbed_create)
        self.stubs.Set(db, 'task_get_all', stubbed_get_all)
        self.stubs.Set(api, '_make_task_dict', lambda t: t)
        self.stubs.Set(common_utils, 'execute', stubbed_execute)

    def assertProperlyGeneratedCron(self, recurrence, expected):
        body = {'action': 'snapshot', 'instance_uuid': 'abcdef',
                'recurrence': recurrence}
        res = self.app.put('/periodic_tasks/%s' % TEST_UUID,
                            content_type='application/json',
                            data=json.dumps(body))
        self.assertEqual(res.status_code, 202)
        self.assertEqual(self.stub_rvs['cmd'], ['crontab', '-'])

        expected_stdin = '%s tempo-enqueue %s\n' % (expected, TEST_UUID)
        self.assertEqual(self.stub_rvs['stdin'], expected_stdin)

    def test_create_hourly_start_at_beginning_of_hour(self):
        self.assertProperlyGeneratedCron('0 * *', '0 * * * *')

    def test_create_daily_start_at_midnight(self):
        self.assertProperlyGeneratedCron('0 0 *', '0 0 * * *')

    def test_create_weekly_start_on_sunday_at_midnight(self):
        self.assertProperlyGeneratedCron('0 0 0', '0 0 * * 0')
