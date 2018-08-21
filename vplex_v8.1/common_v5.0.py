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

import sys

from oslo_config import cfg
from oslo_log import log as logging

from cinder import exception
from cinder.i18n import _
from cinder.volume import configuration
from cinder.volume.drivers.dell_emc.vplex import adapter
from cinder.volume.drivers.dell_emc.vplex import rest
from cinder.volume.drivers.dell_emc.vplex import utils
LOG = logging.getLogger(__name__)

CONF = cfg.CONF

CINDER_EMC_CONFIG_FILE = '/etc/cinder/cinder_emc_vplex_config.xml'

vplex_opts = [
    cfg.StrOpt('cinder_emc_config_file',
               default=CINDER_EMC_CONFIG_FILE,
               deprecated_for_removal=True,
               help='Use this file for cinder emc plugin '
                    'config data.')]

CONF.register_opts(vplex_opts, group=configuration.SHARED_CONF_GROUP)


class VMAXCommon(object):
    """Common class for Rest based VPLEX volume drivers.

    This common class is for Dell EMC VPLEX volume drivers
    based on UniSphere Rest API.
    """
    vplex_info = {'backend_name': None,
                 'config_file': None,
                 'arrayinfo': None}

    def __init__(self, protocol, version, configuration=None,
                 active_backend_id=None):

        self.protocol = protocol
        self.configuration = configuration
        self.configuration.append_config_values(vplex_opts)
        self.rest = rest.VPLEXRest()
        self.utils = utils.VPLEXUtils()
        self.adapter = adapter.VPLEXAdapter(protocol, self.rest)
        self.version = version
        self._gather_info()

    def get_attributes_from_vplex_config(self):
        """
            cinder_emc_vplex_config.xml
        :return: kwargs
        """
        kwargs = self.utils.parse_file_to_get_array_map(
                self.vplex_info['config_file'])
        LOG.debug('the vplex config info : %(args)s',
                  {'args': kwargs})
        return kwargs

    def get_attributes_from_cinder_config(self):
        """
            cinder.conf
            Get relevent details from configuration file.
        """
        if hasattr(self.configuration, 'cinder_emc_config_file'):
            self.vplex_info['config_file'] = (
                self.configuration.cinder_emc_config_file)
        else:
            self.vplex_info['config_file'] = (
                self.configuration.safe_get('cinder_emc_config_file'))
        self.vplex_info['backend_name'] = (
            self.configuration.safe_get('volume_backend_name'))
        LOG.debug(
            "Updating volume stats on file %(emcConfigFileName)s on "
            "backend %(backendName)s.",
            {'emcConfigFileName': self.vplex_info['config_file'],
             'backendName': self.vplex_info['backend_name']})

    def _gather_info(self):
        """Gather the relevant information for update_volume_stats."""
        self.get_attributes_from_cinder_config()
        # gather vplex info
        arrayinfo = self.get_attributes_from_vplex_config()
        self.vplex_info['arrayinfo'] = arrayinfo

    def update_volume_stats(self):
        """Retrieve stats info."""
        # Dictionary to hold the arrays for which the vplex details
        # have already been queried.
        backend_name = self.vplex_info['backend_name']
        array_info = self.vplex_info['arrays_info']
        emc_size = array_info['count']
        cluster_list = []
        for index in range(emc_size):
            cluster = array_info['emc'][index]['vplex']['Cluster']
            cluster_list.append(cluster)
        self.rest.set_rest_credentials(array_info)

        volume_dict = self.adapter.get_details_from_storage(
                cluster_list)
        total_capacity_gb = volume_dict['total_capacity_gb']
        free_capacity_gb = volume_dict['free_capacity_gb']
        provisioned_capacity_gb = volume_dict['provisioned_capacity_gb']
        array_reserve_percent = volume_dict['reserved_percentage']

        data_dict = {'vendor_name': "Dell EMC",
                'driver_version': self.version,
                'storage_protocol': self.protocol,
                'volume_backend_name': backend_name or
                                       self.__class__.__name__,
                # Use capacities here .
                'total_capacity_gb': total_capacity_gb,
                'free_capacity_gb': free_capacity_gb,
                'provisioned_capacity_gb': provisioned_capacity_gb,
                'reserved_percentage': array_reserve_percent}

        return data_dict

    def _get_volume_extra_specs(self, volume, group, connector,
                                workload, slo, count):
        """ get volume extra specs

        :param volume:
        :param group:
        :return:
        """
        volume_extra_specs = {}
        cg_name = self.utils.truncate_string(group['id'], 8)
        volume_name = 'OS-' + volume['id'] + '_' + 'VOL'
        cg_attribute = cg_name + '::visibilty'
        visibility = 'cluster-1, cluster-2'
        lun_list = []
        device_list = []
        extent_list = []
        pool = []
        port_list = []
        sv_list = []
        initiator_ports = []

        for index in range(count):
            lun_name = 'OS-' + volume['id'] + '-' + 'LUN' + '-' + index
            device_name = 'device_' + lun_name + "_1"
            extent_name = 'extent_' + lun_name + '_1'
            lun_list.append(lun_name)
            device_list.append(device_name)
            extent_list.append(extent_name)
            host_name = connector['host']
            port = connector['wwpn']

            sv_name = (
                "OS-%(HostName)s-%(pool)s-%(slo)s-%(workload)s-%(protocol)s"
                "-SV" % {'HostName': host_name,
                   'pool': pool[index],
                   'slo': slo[index],
                   'workload': workload[index],
                   'protocol': self.protocol})
            initiator_port = (
                "OS-%(HostName)s-%(pool)s-%(slo)s-%(workload)s-%(protocol)s"
                "-PG" % {'HostName': host_name,
                   'pool': pool[index],
                   'slo': slo[index],
                   'workload': workload[index],
                   'protocol': self.protocol})

            sv_list.append(sv_name)
            initiator_ports.append(initiator_port)
            port_list.append(port)
        volume_extra_specs.update({'lun': lun_list})
        volume_extra_specs.update({'device': device_list})
        volume_extra_specs.update({'extent': extent_list})
        volume_extra_specs.update({'volume_name': volume_name})

        # geometry   -->>> default:raid-0
        volume_extra_specs.update({'geometry': 'raid-0'})
        volume_extra_specs.update({'cg_name': cg_name})
        volume_extra_specs.update({'delay': '5s'})
        volume_extra_specs.update({'attributes': cg_attribute})
        volume_extra_specs.update({'visibility': visibility})
        volume_extra_specs.update({'sv_name': sv_list})
        volume_extra_specs.update({'initiator_port': initiator_ports})
        volume_extra_specs.update({'port': port_list})

        return volume_extra_specs

    def _set_vplex_extra_specs(self, volume, group, array_info, connector):
        """vplex for volume and

        :param volume:
        :param group:
        :param array_info:
        :param connector:
        :return:
        """
        hard_list = []
        storage_volumes = []
        cluster_list = []
        pool = []
        slo = []
        workload = []
        portGroup = []
        count = self.vplex_info['arrayinfo']['count']

        for index in range(count):
            hard_name = array_info['emc'][index]['vplex']['EMC-SYMMETRIX']
            storage_volume_name = array_info['emc'][index]['vplex']['VPD83T3']
            cluster_name = array_info['emc'][index]['vplex']['Cluster']
            pool_name = array_info['emc'][index]['vplex']['Pool']
            slo_name = array_info['emc'][index]['vplex']['SLO']
            workload_name = array_info['emc'][index]['vplex']['WORKLOAD']
            port_group = array_info['emc'][index]['vplex']['PortGroup']

            hard_list.append(hard_name)
            storage_volumes.append(storage_volume_name)
            cluster_list.append(cluster_name)
            pool.append(pool_name)
            slo.append(slo_name)
            workload.append(workload_name)
            portGroup.append(port_group)
        # get info from vplex xml
        array_info_spec = {'hards': hard_list,
                           'storage_volumes': storage_volumes,
                           'cluster_name': cluster_name,
                           'pool': pool,
                           'slo': slo,
                           'workload': workload,
                           'port_group': portGroup
                           }
        # get info from volume
        volume_extra_specs = self._get_volume_extra_specs(volume,
                                                          group,
                                                          connector,
                                                          workload,
                                                          slo,
                                                          count)

        extra_specs = {'array_info': array_info_spec,
                       'volume_info': volume_extra_specs}
        return extra_specs

    def _initial_setup(self, volume, group=None, connector=None):
        """Necessary setup to accumulate the relevant information.

        The volume object has a host in which we can parse the
        config group name. The config group name is the key to our EMC
        configuration file. The emc configuration file contains srp name
        and array name which are mandatory fields.
        :param volume: the volume object
        :param group: optional group
        :returns: dict -- extra spec dict
        :raises: VolumeBackendAPIException:
        """
        try:
            array_info = self.get_attributes_from_vplex_config()
            if not array_info:
                exception_message = (_(
                    "Unable to get corresponding record for vplex."))
                raise exception.VolumeBackendAPIException(
                    data=exception_message)

            self.rest.set_rest_credentials(array_info)

            extra_specs = self._set_vplex_extra_specs(volume, group,
                                                      array_info, connector)
        except Exception:
            exception_message = (_(
                "Unable to get configuration information necessary to "
                "create a volume: %(errorMessage)s.")
                % {'errorMessage': sys.exc_info()[1]})
            raise exception.VolumeBackendAPIException(data=exception_message)
        return extra_specs

    def create_volume(self, volume):
        """Creates a EMC(VPLEX) volume

        :param volume: volume object
        """
        extra_specs = self._initial_setup(volume)
        try:
            LOG.info("Beginning create volume process")
            self.adapter.create_volume(
                volume, extra_specs)
        except Exception:
            LOG.error("Create volume failed..")
            raise

    def delete_volume(self, volume):
        """Deletes a EMC(VPLEX) volume

        :param volume: volume object
        """
        extra_specs = self._initial_setup(volume)
        LOG.info("Beginning create volume process")
        self.adapter.delete_volume(volume, extra_specs)
        LOG.info("The @(volume)s has been deleted .",
                 {'volume': volume})

    def create_consistencygroup(self, context, group):
        """Creates a consistency group.

        :param context: the context
        :param group: the group object to be created
        :raises: VolumeBackendAPIException
        """
        extraSpecs = self._initial_setup(None, group)
        try:
            LOG.info("Beginning create consistency group process")
            self.provision.create_consistency_group(
                group, extraSpecs)
            LOG.info("created the @(cgName)s consistency group.",
                     {'cgName': group})
        except Exception:
            LOG.error("created the consistency group failed.")
            raise exception.VolumeBackendAPIException()

    def delete_consistencygroup(self, context, group):
        """Deletes a consistency group.

        :param context: the context
        :param group: the group object to be deleted
        :returns: list -- list of volume objects
        :raises: VolumeBackendAPIException
        """
        extraSpecs = self._initial_setup(None, group)

        try:
            LOG.info("Beginning delete consistency group process")
            self.adapter.delete_consistency_group(group,
                                                    extraSpecs)
        except Exception:
            exceptionMessage = (_(
                "Failed to delete consistency group: %(cgName)s.")
                % {'group': group})
            raise exception.VolumeBackendAPIException(data=exceptionMessage)
        return group

    def attach_volume(self, context, volume, instance_uuid, host_name,
                      mountpoint):
        pass

    def detach_volume(self, context, volume, attachment=None):
        pass

    def initialize_connection(self, volume, connector):
        """Initializes the connection and returns device and connection info.

        :param volume: volume Object
        :param connector: the connector Object
        :returns: dict -- deviceInfoDict - device information dict
        :raises: VolumeBackendAPIException
        """
        LOG.info("Initialize connection: %(volume)s.",
                 {'volume': volume})
        extraSpecs = self._initial_setup(volume, None, connector)
        try:
            self.adapter.check_and_create_storage_view(volume, extraSpecs)
        except Exception:
            exception_message = (_(
                        "Unable to attach because of the "
                        "following error: %(errorMessage)s.")
                        % {'errorMessage': extraSpecs})
            raise exception.VolumeBackendAPIException(
                data=exception_message)

    def terminate_connection(self, volume, connector):
        """Disallow connection from connector.

        :params volume: the volume Object
        :params connector: the connector Object
        """
        LOG.info("Terminate connection: %(volume)s.",
                 {'volume': volume['name']})
        extraSpecs = self._initial_setup(volume, None, connector)
        self.adapter.check_and_delete_storage_view(volume, extraSpecs)