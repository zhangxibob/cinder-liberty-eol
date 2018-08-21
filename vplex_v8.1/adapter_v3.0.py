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
import time
import sys

from oslo_log import log as logging

from cinder import exception
from cinder.i18n import _

LOG = logging.getLogger(__name__)


class VPLEXAdapter(object):

    def __init__(self, configuration, rest):
        self.config = configuration
        self.rest = rest
        self.mirror_device_date = None

    def create_volume(self, volume, extra_specs):
        """ create a EMC(VPLEX) volume

        :param volume:
        :param extra_specs:
        :return:
        """
        cluster_1ist = extra_specs['array-info']['cluster_name']
        hard_list = extra_specs['array-info']['hards']
        storage_volume_list = extra_specs['array-info']['storage_volumes']
        lun_list = extra_specs['volume_info']['lun']
        device_list = extra_specs['volume_info']['device']
        extent_list = extra_specs['volume_info']['extent']
        volume_name = extra_specs['volume_info']['volume_name']
        geometry = extra_specs['volume_info']['geometry']
        start_time = time.time()
        LOG.debug("Delete volume info: [volume :%(volume_name)s,"
                  "hards:%(hards)s, storage_volumes:%(storage_volumes)s"
                  "luns:%(luns)s, devices:%(devices)s, "
                  "extents:%(extents)s, geometry:%(geometry)s].",
                  {'volume_name': volume_name,
                   'hards': hard_list,
                   'storage_volumes': storage_volume_list,
                   'luns': lun_list,
                   'devices': device_list,
                   'extents': extent_list,
                   'geometry': geometry})
        try:
            # create volume for cluster-1/2
            size = extra_specs['volume_info']['count']
            attach_device = ''
            mirror_device = ''
            for index in range(size):
                if index == 0:
                    attach_device = device_list[index]
                if index == 1:
                    mirror_device = device_list[index]
                self.rest.re_discovery_arrays(cluster_1ist[index],
                                              hard_list[index])
                self.rest.claim_storage_volume(lun_list[index],
                                               storage_volume_list[index])
                self.rest.create_extent(lun_list[index])
                self.rest.create_local_device(device_list[index],
                                              extent_list[index],
                                              geometry)

            self.rest.create_virtual_volume(attach_device)
            self.rest.attach_mirror_device(attach_device, mirror_device)
            # update the attach mirror device date
            self.mirror_device_date = time.time()
            LOG.debug("Create volume took: %(delta)s H:MM:SS.",
                      {'delta': self.utils.get_time_delta(start_time,
                                                      time.time())})
        except exception.VolumeBackendAPIException:
            raise

    def delete_volume(self, volume, extra_specs):
        """delete volume

        :param volume:
        :param extra_specs:
        """
        volume_name = extra_specs['volume_info']['volume_name']
        cgName = extra_specs['volume_info']['cg_name']
        hard_list = extra_specs['array-info']['hards']
        lun_list = extra_specs['volume_info']['lun']
        device_list = extra_specs['volume_info']['device']
        extent_list = extra_specs['volume_info']['extent']

        LOG.debug("Delete volume info: [volume :%(volume_name)s,"
                  "cgName:%(cgName)s, devices:%(devices)s "
                  "extents:%(extents)s.",
                  {'volume_name': volume_name,
                   'cgName': cgName,
                   'devices': device_list,
                   'extents': extent_list})

        try:
            attach_device = ''
            mirror_device = ''
            size = extra_specs['volume_info']['count']
            for index in range(size):
                if index == index:
                    attach_device = device_list[index]
                if index == 1:
                    mirror_device = device_list[index]
            self.rest.consistency_group_remove_virtual_volumes(cgName,
                                                               volume_name)
            self.rest.destroy_virtual_volume(volume_name)
            self.rest.detach_mirror_device(attach_device, mirror_device)

            # return device  cluster-1/2
            for index in range(size):
                if index == index:
                    device_name_date = device_list[index] + \
                                       self.mirror_device_date

                    self.rest.destroy_distributed_devices(device_list[index])
                    self.rest.destroy_local_device(device_name_date)
                else:
                    self.rest.destroy_local_device(device_list[index])
                self.rest.destroy_extent(extent_list[index])
                self.rest.unclaim_storage_volume(lun_list[index])
                self.rest.forget_storage_volume(hard_list[index])

        except Exception:
            raise exception.VolumeBackendAPIException

    def create_consistencygroup(self, group, extra_specs):
        """Creates a consistency group.

        :param context: the context
        :param group: the group object to be created
        """
        cg_name = extra_specs['volume_info']['cg_name']
        cluster_1ist = extra_specs['array-info']['cluster_name']
        attributes = extra_specs['volume_info']['attributes']
        visibility = extra_specs['volume_info']['visibility']
        delay = extra_specs['volume_info']['delay']
        volume_name = extra_specs['volume_info']['volume_name']
        cluster_name = ''
        size = extra_specs['volume_info']['count']
        for index in range(size):
            if index == 0:
                cluster_name = cluster_1ist[index]
        LOG.debug('Creates a consistency group info:{ cg_name: %(cg_name)s,'
                  'cluster_name: %(cluster_name)s,'
                  'attributes: %(attributes)s,'
                  'visibility: %(visibility)s，'
                  'delay: %(delay)s,'
                  'volume_name: %(volume_name)s',
                  {'cg_name': cg_name,
                   'cluster_name': cluster_name,
                   'attributes': attributes,
                   'visibility': visibility,
                   'delay': delay,
                   'volume_name': volume_name})
        try:
            self.rest.create_consistency_group(cg_name, cluster_name)
            self.rest.set_consistency_group_visibility(attributes, visibility)
            self.rest.set_detachrule_to_consistency_group(cluster_name,
                                                          delay,
                                                          cg_name)
            self.rest.add_virtualvolumes_to_consistency_group(volume_name,
                                                              cg_name)
        except Exception:
            raise

    def delete_consistency_group(self, group, extraSpecs):
        """delete_consistency_group

        :param cgName:
        :param extraSpecs:
        :return:
        """
        cgName = extraSpecs['volume_info']['cg_name']
        LOG.debug('delete consistency group ->cgName: %(cgName)s,',
                  {'cgName': cgName})
        self.rest.destroy_consistency_group(cgName)

    def check_and_create_storage_view(self, volume, extraSpecs):
        """check_and_create_storage_view

        :param volume:
        :param maskingViewDict:
        """
        cluster_1ist = extraSpecs['array-info']['cluster_name']
        sv_name = extraSpecs['volume_info']['sv_name']
        ports = extraSpecs['array_info']['port_group']
        initiator_port = extraSpecs['volume_info']['initiator_port']
        port = extraSpecs['volume_info']['port']
        virtual_volume = extraSpecs['volume_info']['virtual_volume']
        try:
            LOG.debug('create storage views info:{ sv_name: %(sv_name)s,'
                      'cluster_1ist: %(clusters)s,'
                      'ports: %(ports)s,'
                      'initiator_port: %(initiator_port)s，'
                      'virtual_volumes: %(virtual_volumes)s,'
                      'port: %(port)s',
                      {'sv_name': sv_name,
                       'clusters':cluster_1ist,
                       'ports': ports,
                       'initiator_port': initiator_port,
                       'port': port,
                       'virtual_volumes': virtual_volume})
            size = extraSpecs['volume_info']['count']
            for index in range(size):
                self.rest.create_export_storage_view(cluster_1ist[index],
                                                     sv_name[index],
                                                     ports[index])
                self.rest.register_export_initiator_port(
                        cluster_1ist[index],
                        initiator_port[index],
                        port[index])
                self.rest.addinitiatorport_to_export_storage_view\
                    (sv_name[index], initiator_port[index])
                self.rest.addport_to_export_storage_view(sv_name[index],
                                                         ports[index])
                self.rest.addvirtualvolume_to_export_storage_view(
                        sv_name[index], virtual_volume)
        except Exception:
            raise

    def check_and_delete_storage_view(self, volume, extraSpecs):
        """check_and_delete_storage_view

        :param volume:
        """
        sv_name = extraSpecs['volume_info']['sv_name']
        ports = extraSpecs['array_info']['port_group']
        initiator_port = extraSpecs['volume_info']['initiator_port']
        virtual_volume = extraSpecs['volume_info']['virtual_volume']
        try:
            LOG.debug('delete storage views info:{ sv_name: %(sv_name)s,'
                      'ports: %(ports)s,'
                      'initiator_port: %(initiator_port)s，'
                      'virtual_volumes: %(virtual_volumes)s',
                      {'sv_name': sv_name,
                       'ports': ports,
                       'initiator_port': initiator_port,
                       'virtual_volumes': virtual_volume})
            size = extraSpecs['volume_info']['count']
            for index in range(size):
                self.rest.removeinitiatorport_export_storage_view(
                        sv_name[index], initiator_port[index])
                self.rest.removeport_export_storage_view(
                        sv_name[index], ports[index])
                self.rest.removevirtualvolume_export_storage_view(
                        virtual_volume, sv_name[index])
                self.rest.destroy_export_storage_view(sv_name[index])
                self.rest.unregister_export_initiator_port(
                        initiator_port[index])
        except Exception:
            raise

    def get_details_from_storage(self, cluster_list):
        """get detils from storage

        :param cluster_list:
        :return:
        """
        storages_info = {}
        size = len(cluster_list)
        min_storage = sys.maxsize
        detail_dict = {}
        try:
            for index in range(size):
                storages_json = self.rest.get_details_from_storage(
                        cluster_list[index])
                storage_list = storages_json['attributes']
                total_capacity_gb = 0
                provisioned_capacity_gb = 0
                free_capacity_gb = 0
                reserved_percentage = 0
                for storage in storage_list:
                    if storage['Use'] == 'use' or storage['Use'] == 'claim':
                        total_capacity_gb += storage['Capacity']
                    elif storage['Use'] == 'use':
                        provisioned_capacity_gb += storage['Capacity']
                    else:
                        free_capacity_gb += storage['Capacity']
                if min_storage > total_capacity_gb:
                    min_storage = total_capacity_gb
                    reserved_percentage = round(free_capacity_gb /
                                                total_capacity_gb * 100, 2)
                    detail_dict.update({'total_capacity_gb':
                                            total_capacity_gb})
                    detail_dict.update({'provisioned_capacity_gb':
                                            provisioned_capacity_gb})
                    detail_dict.update({'free_capacity_gb': free_capacity_gb})
                    detail_dict.update({'reserved_percentage':
                                            reserved_percentage})
            LOG.debug('details of storages:{ total_capacity_gb: '
                      '%(total_capacity_gb)s,'
                      'provisioned_capacity_gb: %(provisioned_capacity_gb)s,'
                      'free_capacity_gb: %(free_capacity_gb)s，'
                      'reserved_percentage: %(reserved_percentage)s',
                      {'total_capacity_gb': total_capacity_gb,
                       'provisioned_capacity_gb': provisioned_capacity_gb,
                       'free_capacity_gb': free_capacity_gb,
                       'reserved_percentage': reserved_percentage})
            storages_info.update(detail_dict)
        except Exception:
            raise

        return storages_info



