#!/usr/bin/python
# Copyright (c) 2010 OpenStack, LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import subprocess

from setuptools import setup, find_packages
from setuptools.command.sdist import sdist


setup(
    name='tempo',
    version='0.12',
    description='Tempo Service',
    license='Apache License (2.0)',
    author='OpenStack',
    author_email='openstack@lists.launchpad.net',
    url='http://tempo.openstack.org/',
    packages=find_packages(exclude=['tests', 'bin']),
    test_suite='nose.collector',
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'Environment :: No Input/Output (Daemon)',
    ],
    scripts=['bin/tempo-api',
             'bin/tempo-snapshot',
             'bin/tempo-cron-snapshot',
             'bin/nova-snapshot.sh',
             'bin/tempo-backup',
             'bin/tempo-cron-backup',
             'bin/nova-backup.sh'])

