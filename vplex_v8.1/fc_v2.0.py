# Copyright (c) 2017 Dell Inc. or its subsidiaries.
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

from oslo_log import log as logging

from cinder.volume import driver
from cinder.volume.drivers.dell_emc.vplex import common
from cinder.zonemanager import utils as fczm_utils

LOG = logging.getLogger(__name__)


class EMCVPLEXFCDriver(driver.FibreChannelDriver):
	"""FC Drivers for VPLEX using REST.

	"""

	VERSION = "1.0.0"

	def __init__(self):
		self.common = common.VMAXCommon(
            'FC',
			self.VERSION)

	def create_volume(self, volume):
		"""Creates a VPLEX volume.

		:param volume: the cinder volume object
        """
		self.common.create_volume(volume)

	def delete_volume(self, volume):
		"""Deletes a VMAX volume.

        :param volume: the cinder volume object
        """
		self.common.delete_volume(volume)

	def create_consistencygroup(self, context, group):
		"""Creates a consistencygroup."""
		self.common.create_consistencygroup(context, group)

	def delete_consistencygroup(self, context, group):
		"""Deletes a consistency group."""
		return  self.common.delete_consistencygroup(context, group)

	def attach_volume(self, context, volume, instance_uuid, host_name,
                      mountpoint):
		# Callback for volume attached to instance or host.
		pass

	def detach_volume(self, context, volume, attachment=None):
		# Callback for volume detached.
		pass

	@fczm_utils.AddFcZone
	def initialize_connection(self, volume, connector):
		# Initializes the connection and returns device and connection info.
		LOG.debug("Start FC attach process for volume: %(volume)s.",
                  {'volume': volume['name']})
		return self.common.initialize_connection(volume, connector)

	@fczm_utils.RemoveFcZone
	def terminate_connection(self, volume, connector, **kwargs):
		# Disallow connection from connector.
		LOG.debug("Start FC detach process for volume: %(volume)s.",
                  {'volume': volume['name']})
		self.common.terminate_connection(volume, connector)

	def update_volume_stats(self):
		"""update volume status

		:return:
		"""
		self.common.update_volume_stats()