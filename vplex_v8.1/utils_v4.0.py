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

import datetime
import random
import six
from xml.dom import minidom

LOG = logging.getLogger(__name__)


class VPLEXUtils(object):

    def __init__(self):
        """Utility class for Rest based VMAX volume drivers."""

    def _get_random_portgroup(self, element):
        """Randomly choose a portgroup from list of portgroups.

        :param element: the parent element
        :returns: the randomly chosen port group
        """
        portgroupelements = element.getElementsByTagName('PortGroup')
        if portgroupelements and len(portgroupelements) > 0:
            portgroupnames = [portgroupelement.childNodes[0].nodeValue.strip()
                              for portgroupelement in portgroupelements
                              if portgroupelement.childNodes]
            portgroupnames = list(set(filter(None, portgroupnames)))
            pg_len = len(portgroupnames)
            if pg_len > 0:
                return portgroupnames[random.randint(0, pg_len - 1)]
        return None

    def _get_vplex_wwpns(self, element):
        """Get VPLEX initiator wwpn list.

        :param element: the parent element
        :returns: the wwpns
        """
        wwpn_names = None
        wwpn_elements = element.getElementsByTagName('WWPN')
        if wwpn_elements and len(wwpn_elements) > 0:
            wwpn_names = [wwpn_element.childNodes[0].nodeValue.strip()
                          for wwpn_element in wwpn_elements
                          if wwpn_element.childNodes]
            wwpn_names = list(set(filter(None, wwpn_names)))
        return wwpn_names

    def _process_tag(self, element, tag_name):
        """Process the tag to get the value.

        :param element: the parent element
        :param tag_name: the tag name
        :returns: nodeValue(can be None)
        """
        node_value = None
        try:
            processed_element = element.getElementsByTagName(tag_name)[0]
            node_value = processed_element.childNodes[0].nodeValue
            if node_value:
                node_value = node_value.strip()
        except IndexError:
            pass
        return node_value

    def _get_vplex_connection_info(self, rest_element):
        """Given the filename get the rest server connection details.

        :param rest_element: the rest element
        :returns: dict -- connargs - the connection info dictionary
        :raises: VolumeBackendAPIException
        """
        connargs = {
            'MgmtServerIp': (
                self._process_tag(rest_element, 'MgmtServerIp')),
            'MgmtServerPort': (
                self._process_tag(rest_element, 'MgmtServerPort')),
            'Username': (
                self._process_tag(rest_element, 'Username')),
            'Password': (
                self._process_tag(rest_element, 'Password')),
            'SLO': (
                self._process_tag(rest_element, 'SLO')),
            'Workload': (
                self._process_tag(rest_element, 'Workload')),
            'Array': (
                self._process_tag(rest_element, 'Array')),
            'VPD83T3': (
                self._process_tag(rest_element, 'VPD83T3')),
            'EMC-SYMMETRIX': (
                self._process_tag(rest_element, 'EMC-SYMMETRIX')),
            'Pool': (
                self._process_tag(rest_element, 'Pool')),
			'Cluster': (
                self._process_tag(rest_element, 'Cluster'))
            }

        for k, __ in connargs.items():
            if connargs[k] is None:
                exception_message = (
                    "MgmtServerIp, TargetPort, Username, "
                    "Password, SLO, Workload, Array, Pool must have "
                    "valid values.")
                # raise Exception
                    # Todo

        return connargs

    def _get_vmax_connection_info(self, rest_element):
        """Given the filename get the rest server connection details.

        :param rest_element: the rest element
        :returns: dict -- connargs - the connection info dictionary
        :raises: VolumeBackendAPIException
        """
        connargs = {
            'EcomServerIp': (
                self._process_tag(rest_element, 'EcomServerIp')),
            'EcomServerPort': (
                self._process_tag(rest_element, 'EcomServerPort')),
            'EcomUserName': (
                self._process_tag(rest_element, 'EcomUserName')),
            'EcomPassword': (
                self._process_tag(rest_element, 'EcomPassword')),
            'SLO': (
                self._process_tag(rest_element, 'SLO')),
            'Workload': (
                self._process_tag(rest_element, 'Workload')),
            'Array': (
                self._process_tag(rest_element, 'Array')),
            'Pool': (
                self._process_tag(rest_element, 'Pool'))
            }

        for k, __ in connargs.items():
            if connargs[k] is None:
                exception_message = (
                    "EcomServerIp, EcomServerPort, EcomUserName, "
                    "EcomPassword, SLO, Workload, Array, Pool must have "
                    "valid values.")
                # raise Exception
                    # Todo

        return connargs

    def parse_file_to_get_array_map(self, file_name):
        """Parses a file and gets array map.

        Given a file, parse it to get array info.

        .. code:: ini

          <EMCS>
            <EMC>
                <VMAX>
                    <EcomServerIp>xx.xx.xx.28</EcomServerIp>
                    <EcomServerPort>5989</EcomServerPort>
                    <EcomUserName>xx</EcomUserName>
                    <EcomPassword>xx</EcomPassword>
                    <HBA>wwpn-info</HBA>
                    <SLO>xxx</SLO>
                    <Workload>xxx</Workload>
                    <PortGroups>
                        <PortGroup>xx</PortGroup>
                    </PortGroups>
                    <Array>xx</Array>
                    <Pool>FCPool</Pool>
                </VMAX>
                <VPLEX>
                    <MgmtServerIp>xx.xx.xx.29</MgmtServerIp>
                    <TargetPort>5989</TargetPort>
                    <Username>xx</Username>
                    <Password>xx</Password>
                    <InitialPort>22</InitialPort>
                    <PortGroups>
                        <PortGroup>xx</PortGroup>
                    </PortGroups>
                    <Array>xx</Array>
                    <Pool>FCPool</Pool>
                </VPLEX>
            </EMC>
            <EMC>
                <VMAX>
                    <EcomServerIp>xx.xx.xx.30</EcomServerIp>
                    <EcomServerPort>5989</EcomServerPort>
                    <EcomUserName>xx</EcomUserName>
                    <EcomPassword>xx</EcomPassword>
                    <HBA>wwpn-info</HBA>
                    <PortGroups>
                        <PortGroup>xx</PortGroup>
                    </PortGroups>
                    <Array>xx</Array>
                    <Pool>FCPool</Pool>
                </VMAX>
                <VPLEX>
                    <MgmtServerIp>xx.xx.xx.31</MgmtServerIp>
                    <TargetPort>5989</TargetPort>
                    <Username>xx</Username>
                    <Password>xx</Password>
                    <InitialPort>22</InitialPort>
                    <PortGroups>
                        <PortGroup>xx</PortGroup>
                    </PortGroups>
                    <Array>xx</Array>
                    <Pool>FCPool</Pool>
                </VPLEX>
            </EMC>
        </EMCS>

        :param file_name: the configuration file
        :returns: array_map
            {'emcs': [{'vmax': {}, 'vplex': {}},
		      {'vmax': {}, 'vplex': {}}]}
        """
        LOG.warning("Use of xml file in backend configuration is deprecated "
                    "in Queens and will not be supported in future releases.")
        emc_cfg_file_xml = open(file_name, 'r')
        data = emc_cfg_file_xml.read()
        emc_cfg_file_xml.close()
        dom = minidom.parseString(data)

        array_map = None
        array_map_item = []
		emc_count = 0
        try: 
            dom_emcs = dom.getElementsByTagName('EMC')
			emc_count = len(dom_emcs)
            for dom_emc in dom_emcs:
                emc_dict = {}

                dom_emc_vmax = dom_emc.getElementsByTagName('VMAX')[0]
                vmax_connargs = self._get_vmax_connection_info(dom_emc_vmax)
                vmax_portgroup = self._get_random_portgroup(dom_emc_vmax)
                vmax_kwargs = {'vmax': {
                    'EcomServerIp': vmax_connargs['EcomServerIp'],
                    'EcomServerPort': vmax_connargs['EcomServerPort'],
                    'EcomUserName': vmax_connargs['EcomUserName'],
                    'EcomPassword': vmax_connargs['EcomPassword'],
                    'SLO': vmax_connargs['SLO'],
                    'Workload': vmax_connargs['Workload'],
                    'Array': vmax_connargs['Array'],
                    'Pool': vmax_connargs['Pool'],
                    'PortGroup': vmax_portgroup}}
                emc_dict.update(vmax_kwargs)

                dom_emc_vplex = dom_emc.getElementsByTagName('VPLEX')[0]
                vplex_connargs = self._get_vplex_connection_info(dom_emc_vplex)
                vplex_portgroup = self._get_random_portgroup(dom_emc_vplex)
                vplex_wwpns = self._get_vplex_wwpns(dom_emc_vplex)
                vplex_kwargs = {'vplex': {
                    'MgmtServerIp': vplex_connargs['MgmtServerIp'],
                    'MgmtServerPort': vplex_connargs['MgmtServerPort'],
                    'Username': vplex_connargs['Username'],
                    'Password': vplex_connargs['Password'],
                    'SLO': vplex_connargs['SLO'],
                    'Workload': vplex_connargs['Workload'],
                    'Array': vplex_connargs['Array'],
                    'Pool': vplex_connargs['Pool'],
                    'VPD83T3': vplex_connargs['VPD83T3'],
                    'EMC-SYMMETRIX': vplex_connargs['EMC-SYMMETRIX'],
                    'PortGroup': vplex_portgroup,
                    'wwpns': vplex_wwpns,
					'Cluster': vplex_connargs['Cluster']}}
                emc_dict.update(vplex_kwargs)

                array_map_item.append(emc_dict)

            array_map = {'emc': array_map_item, 'count': emc_cout}

        except IndexError:
            pass

        return array_map

    def truncate_string(self, strToTruncate, maxNum):
        """Truncate a string by taking first and last characters.

        :param strToTruncate: the string to be truncated
        :param maxNum: the maximum number of characters
        :returns: string -- truncated string or original string
        """
        if len(strToTruncate) > maxNum:
            newNum = len(strToTruncate) - maxNum / 2
            firstChars = strToTruncate[:maxNum / 2]
            lastChars = strToTruncate[newNum:]
            strToTruncate = firstChars + lastChars

        return strToTruncate

    @staticmethod
    def get_time_delta(start_time, end_time):
        """Get the delta between start and end time.

        :param start_time: the start time
        :param end_time: the end time
        :returns: string -- delta in string H:MM:SS
        """
        delta = end_time - start_time
        return six.text_type(datetime.timedelta(seconds=int(delta)))