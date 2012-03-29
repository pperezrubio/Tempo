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

import logging
import logging.config
import traceback

from tempo import config
from tempo.openstack.common import cfg

CFG = config.CFG

log_opts = [
    cfg.StrOpt('file_config',
                default=None,
                help='Path to logging config file')
]

log_group = cfg.OptGroup(name='log', title='Tempo Log options')
CFG.register_group(log_group)
CFG.register_opts(log_opts, group=log_group)


def setup():
    if CFG.log.file_config:
        try:
            logging.config.fileConfig(CFG.log.file_config)
        except Exception:
            traceback.print_exc()
            raise
    else:
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

        if CFG.debug:
            level = logging.DEBUG
        else:
            level = logging.WARN

        root_logger.setLevel(level)
        stream_handler = logging.StreamHandler()
        root_logger.addHandler(stream_handler)
