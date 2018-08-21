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

from cinder import exception
from cinder.i18n import _
import requests
from requests.auth import HTTPBasicAuth
import six

LOG = logging.getLogger(__name__)

# HTTP constants
GET = 'GET'
POST = 'POST'
PUT = 'PUT'
DELETE = 'DELETE'
STATUS_200 = 200
STATUS_201 = 201
STATUS_202 = 202
STATUS_204 = 204


class VPLEXRest(object):

    def __init__(self):
        self.user = None
        self.passwd = None
        self.base_uri = None

    def set_rest_credentials(self, array_info):
        """Given the array record set the rest server credentials.

        :param array_info: record
        """
        ip = array_info['emc'][0]['vplex']['MgmtServerIp']
        port = array_info['emc'][0]['vplex']['MgmtServerPort']
        self.user = array_info['emc'][0]['vplex']['Username']
        self.passwd = array_info['emc'][0]['vplex']['Password']
        ip_port = "%(ip)s:%(port)s" % {'ip': ip, 'port': port}
        self.base_uri = ("https://%(ip_port)s/vplex" % {'ip_port': ip_port})

    def _build_uri(resource_type):
        """Build the target url.

        :param resource_type: the resource type e.g. maskingview
        :returns: target url, string
        """
        target_uri = ('/%(resource_type)s'
                      % {'resource_type': resource_type})
        return target_uri

    def request(self, method, target_uri, params=None):
        """Sends a request (GET, POST, PUT, DELETE) to the target api.

        :param target_uri: target uri (string)
        :param method: The method (GET, POST, PUT, or DELETE)
        :param params: Additional URL parameters
        :param request_object: request payload (dict)
        :returns: server response object (dict)
        :raises: VolumeBackendAPIException
        """
        message, status_code = None, None
        url = ("%(self.base_uri)s%(target_uri)s" %
               {'self.base_uri': self.base_uri,
                'target_uri': target_uri})
        try:
            if method == 'GET':
                response = requests.get(url, data=params,
                        auth=HTTPBasicAuth(self.user, self.passwd))
            elif message == 'POST':
                response = requests.post(url, data=params,
                         auth=HTTPBasicAuth(self.user, self.passwd))
            elif message == 'PUT':
                response = requests.put(url, data=params,
                        auth=HTTPBasicAuth(self.user, self.passwd))
            elif message == 'DELETE':
                response = requests.delete(url, data=params,
                       auth=HTTPBasicAuth(self.user, self.passwd))
            else:
                pass
            status_code = response.status_code
            try:
                message = response.json()
            except ValueError:
                LOG.debug("No response received from API. Status code "
                          "received is: %(status_code)s",
                          {'status_code': status_code})
                message = None
            LOG.debug("%(method)s request to %(url)s has returned with "
                      "a status code of: %(status_code)s.",
                      {'method': method, 'url': url,
                       'status_code': status_code})
        except requests.Timeout:
            LOG.error("The %(method)s request to URL %(url)s timed-out, "
                      "but may have been successful. Please check the array.",
                      {'method': method, 'url': url})
        except Exception as e:
            exception_message = (_("The %(method)s request to URL %(url)s "
                                   "failed with exception %(e)s")
                                 % {'method': method, 'url': url,
                                    'e': six.text_type(e)})
            LOG.exception(exception_message)
            raise exception.VolumeBackendAPIException(data=exception_message)

        return status_code, message

    def check_status_code_and_message_success(self, operation, status_code,
                                              message):
        """Check if a status code and message indicates success.

        :param operation: the operation
        :param status_code: the status code
        :param message: the server response
        :raises: VolumeBackendAPIException
        """
        if status_code not in [STATUS_200, STATUS_201,
                               STATUS_202, STATUS_204]:
            exception_message = (
                _('Error %(operation)s. The status code received '
                  'is %(sc)s and the message is %(message)s.')
                % {'operation': operation,
                   'sc': status_code, 'message': message})
            raise exception.VolumeBackendAPIException(
                data=exception_message)

        if message:
            exception_data = message['response']['exception']
            if exception_data is None or exception_data == 'null':
                exception_message = (
                    _('Error %(operation)s. The exception is %(exc)s '
                      'and the message us %(message)s.')
                    % {'operation': operation,
                       'exc': exception_data, 'message': message}
                )
                raise exception.VolumeBackendAPIException(
                    data=exception_message)

    def create_resource(self, resource_type, args):
        """Create a provisioning resource.

        :param resource_type: the resource type
        :param args: the args for body
        """
        target_uri = self._build_uri(resource_type)
        status_code, message = self.request(POST, target_uri,
                                            request_object=args)
        operation = 'Create %(res)s resource' % {'res': resource_type}
        self.check_status_code_and_message_success(
            operation, status_code, message)

    def get_resource(self, resource_type, args):
        """get a provisioning resource.

        :param resource_type: the resource type
        :param args: the args for body
        """
        target_uri = self._build_uri(resource_type)
        status_code, message = self.request(GET, target_uri,
                                            request_object=args)
        operation = 'Create %(res)s resource' % {'res': resource_type}
        self.check_status_code_and_message_success(
            operation, status_code, message)
        return message

    def re_discovery_arrays(self, cluster, hard):
        """ array re-discover

        :param cluster: cluster name
        :param hard: the request hard of host
        """
        new_arrays_data = ({"args" : "-a " + hard + " --cluster " +
                            cluster + " --force"})
        self.create_resource('re-disvovery+arrays', new_arrays_data)

    def claim_storage_volume(self, name, storage_volumes):
        """  claim storage-volume

        :param name: the name of storage-volumes
        :param storage_volumes:
        """
        new_arrays_data = ({"args": "-n " + name + " -d " +
                            storage_volumes + "  --thin-rebuild -f"})
        self.create_resource('storage-volume+claim', new_arrays_data)

    def create_extent(self, storage_volumes):
        """create extent

        :param storage_volumes:
        :return:
        """
        new_arrays_data = ({"args": "-d " + storage_volumes})
        self.create_resource('extent+create', new_arrays_data)

    def create_local_device(self, name, extent, geometry):
        """create local device

        :param name:
        :param extent:
        :param geometry: raid-0
        """
        new_arrays_data = ({"args": "-n " + name + " -e " +
                            extent + "-g" + geometry + " -f"})
        self.create_resource('local-device+create', new_arrays_data)

    def create_virtual_volume(self, device):
        """create virtual volume

        :param device:
        :return:
        """
        new_arrays_data = ({"args": "--device " + device})
        self.create_resource('virtual-volume+create', new_arrays_data)

    def attach_mirror_device(self, device, mirror_device):
        """attach mirror device

        :param device:
        :param mirror_device:
        """
        new_arrays_data = ({"args": "-d " + device + " -m " +
                            mirror_device + " -f"})
        self.create_resource('device+attach-mirror', new_arrays_data)

    def create_consistency_group(self, name, cluster):
        """create consistency-group

        :param name:
        :param cluster:
        """
        new_arrays_data = ({"args": "--name " + name + " --cluster " +
                            cluster + " -f"})
        self.create_resource('consistency-group+create', new_arrays_data)

    def set_consistency_group_visibility(self, attributes, value):
        """set consistency-group visibility

        :param attributes:
        :param value:
        """
        new_arrays_data = ({"args": "-a " + attributes + " -v " +
                            value + " -f"})
        self.create_resource('set', new_arrays_data)

    def set_detachrule_to_consistency_group(self, cluster, delay,
                                            consistency_groups):
        """set detachrule to consistency-group

        :param cluster:
        :param delay:
        :param consistency_groups:
        """
        new_arrays_data = ({"args": "--cluster " + cluster + " --delay " +
                            delay + "--consistency-groups" +
                                    consistency_groups + " -f"})
        self.create_resource('consistency-group+set-detach-rule+winner',
                             new_arrays_data)

    def add_virtualvolumes_to_consistency_group(self, volumes, consistency_group):
        """add virtualvolumes to consistency-group

        :param volumes:
        :param consistency_group:
        """
        new_arrays_data = ({"args": "--virtual-volumes " + volumes +
                            " --consistency-group " + consistency_group +
                                    " -f"})
        self.create_resource('consistency-group+add-virtual-volumes',
                             new_arrays_data)

    def create_export_storage_view(self, cluster, name, ports):
        """create export storage-view

        :param cluster:
        :param name:
        :param ports:
        """
        new_arrays_data = ({"args": "--cluster " + cluster +
                            " --name " + name +
                            " --ports " + ports + " -f"})
        self.create_resource('export+storage-view+create', new_arrays_data)

    def register_export_initiator_port(self, cluster, initiator_port, ports):
        """register export initiator-port

        :param cluster:
        :param initiator_port:
        :param ports:
        """
        port_str = ''
        for index in range(len(ports)):
            port_str += ports[index]
            if index == len(ports)-1:
                break
            port_str += ', '

        new_arrays_data = ({"args": "--cluster " + cluster +
                            " --initiator-port " + initiator_port +
                            " --ports " + port_str + " -f"})
        self.create_resource('export+initiator-port+register', new_arrays_data)

    def addinitiatorport_to_export_storage_view(self, view, initiator_port):
        """addinitiatorport to export storage-view

        :param view:
        :param initiator_port:
        """
        new_arrays_data = ({"args": "--view " + view +
                            " --initiator-ports " + initiator_port +
                            " -f"})
        self.create_resource('export+storage-view+addinitiatorport', new_arrays_data)

    def addport_to_export_storage_view(self, view, ports):
        """ addport to export storage-view

        :param view: MV
        :param ports: ports
        """
        new_arrays_data = ({"args": "--view " + view +
                            " --ports " + ports})
        self.create_resource('export+storage-view+addport', new_arrays_data)

    def addvirtualvolume_to_export_storage_view(self, view, virtual_volumes):
        """export storage-view addvirtualvolume

        :param view: MV
        :param virtual_volumes: volumes
        """
        new_arrays_data = ({"args": "--view " + view +
                            " --virtual-volumes " + virtual_volumes})
        self.create_resource('export+storage-view+addvirtualvolume', new_arrays_data)

    def removeinitiatorport_export_storage_view(self, view, initiator_ports):
        """removeinitiatorport_export_storage_view

        :param view:
        :param initiator_ports:
        """
        new_arrays_data = ({"args": "--view " + view +
                            " --initiator-ports " + initiator_ports})
        self.create_resource('export+storage-view+removeinitiatorport', new_arrays_data)

    def removeport_export_storage_view(self, view, ports):
        """removeport_export_storage_view

        :param view:
        :param ports:
        """
        new_arrays_data = ({"args": "--view " + view +
                            " --ports " + ports})
        self.create_resource('export+storage-view+removeport', new_arrays_data)

    def removevirtualvolume_export_storage_view(self, virtual_volumes, view):
        """removevirtualvolume_export_storage_view

        :param virtual_volumes:
        :param view:
        """
        new_arrays_data = ({"args": "--virtual-volumes " + virtual_volumes +
                            " --view " + view})
        self.create_resource('export+storage-view+removevirtualvolume', new_arrays_data)

    def destroy_export_storage_view(self, view):
        """destroy_export_storage_view

        :param view:
        """
        new_arrays_data = ({"args": " --view " + view})
        self.create_resource('export+storage-view+destroy', new_arrays_data)

    def unregister_export_initiator_port(self, initiator_port):
        """unregister_export_initiator_port

        :param initiator_port:
        """
        new_arrays_data = ({"args": " --initiator-port " + initiator_port})
        self.create_resource('export+initiator-port+unregister', new_arrays_data)

    def consistency_group_remove_virtual_volumes(self, consistency_group,
                                                 virtual_volumes):
        """consistency-group remove-virtual-volumes

        :param consistency_group:
        :param virtual_volumes:
        """
        new_arrays_data = ({"args": "--consistency-group " + consistency_group +
                            " --virtual-volumes " + virtual_volumes})
        self.create_resource('consistency-group+remove-virtual-volumes', new_arrays_data)

    def destroy_virtual_volume(self, virtual_volumes):
        """virtual-volume destroy

        :param virtual_volumes:
        """
        new_arrays_data = ({"args": " --virtual-volumes " + virtual_volumes})
        self.create_resource('virtual-volume+destroy', new_arrays_data)

    def detach_mirror_device(self, device, mirror_device):
        """device detach-mirror

        :param device:
        :param mirror_device:
        """
        new_arrays_data = ({"args": "--device " + device +
                            " -m " + mirror_device})
        self.create_resource('device+detach-mirror', new_arrays_data)

    def destroy_distributed_devices(self, distributed_devices):
        """destroy_distributed_devices

        :param distributed_devices:
        """
        new_arrays_data = ({"args": " --distributed-devices " +
                                    distributed_devices + " -f"})
        self.create_resource('ds+dd+destroy', new_arrays_data)

    def destroy_local_device(self, device):
        """destroy local-device

        :param device:
        """
        new_arrays_data = ({"args": " -d " + device + " -f"})
        self.create_resource('local-device+destroy', new_arrays_data)

    def destroy_extent(self, extent):
        """destroy extent

        :param extent:
        """
        new_arrays_data = ({"args": " -s " + extent+" -f"})
        self.create_resource('extent+destroy ', new_arrays_data)

    def unclaim_storage_volume(self, storage_volume):
        """unclaim storage-volume

        :param storage_volume:
        """
        new_arrays_data = ({"args": " -d " + storage_volume})
        self.create_resource('storage-volume+unclaim', new_arrays_data)

    def forget_storage_volume(self, hard):
        """forget storage-volume

        :param hard:
        """
        new_arrays_data = ({"args": " -d " + hard})
        self.create_resource('storage-volume+forget', new_arrays_data)

    def destroy_consistency_group(self, consistency_groups):
        """destroy consistency-group

        :param consistency_groups:
        """
        new_arrays_data = ({"args": " --consistency-groups " +
                                    consistency_groups + " --force"})
        self.create_resource('consistency-group+destroy', new_arrays_data)

    def get_details_from_storage(self, cluster):
        """ get_details_from_storage

        :param cluster:
        :return:
        """
        path = '/cluster/' + cluster + '/storage-elements/storage-volumes'
        new_arrays_data = ({"args": " -C " + path})
        return self.get_resource('ll', new_arrays_data)