"""
Copyright (C) 2010 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
"""
import re 
import types
import string

#node="/interfaces/eth0/BACnetIP/Network (10001)/Central Plant (100)/CWS Temp (AnalogInput 3)/present_value"
Properties = {}
carrier_name = 'BACnetIP'

def parse_grep_file_into_list(f):
    global carrier_name
    #scan the grep file of all the HTML lines that reference old stype BACnet nodes
    lines = f.readlines()
    f.close()
    answer = []
    re_line=re.compile('(node="/interfaces/eth[0-1]/)(.*?)/(.*?)\"(.*)',re.M|re.S)

    for line in lines:
        m = re_line.search(line)
        if m:
            groups = m.groups()
            answer.append(groups[2])
            #answer.append(m.groups())
    carrier_name = groups[1] #grab the carrier name while we have it. 
    return answer #list of urls of old bacnet points

def convert_node_urls_to_dictionary_tree(urls):
    root = {}
    for url in urls:
        current_dict = root
        for u in url.split('/'): #[network], device,object, property, array index
            if not current_dict.has_key(u):
                current_dict[u]={}
            current_dict = current_dict[u]
    return root

def add_links_to_tree(root):
    link = None
    for k1 in root.keys():
        device = root[k1]
        if 'Network' in k1: #network node, iterate through it's devices
            for k2 in root[k1].keys():
                add_links_to_device(root[k1][k2], k2)
        else:
            add_links_to_device(root[k1], k1)

device_line=re.compile('(.*?)\((.*?)\)(.*)',re.M|re.S) #get the device number from between the "(" and ")" in the string
object_line=re.compile('(.*?)\((.*?)\s(.*?)\)(.*)',re.M|re.S) #get the object ID string from between the "(" and ")" in the string

def add_links_to_device(device, key):
    device_url = device_line.search(key).groups()[1] #the object number (as a string)
    for o in device.keys():
        #add links to object
        object = device[o]
        dummy, object_type_str, object_instance, dummy2 = object_line.search(o).groups()
        object_url = device_url + '/' + Objects[object_type_str] + '/' + object_instance
        for p in object.keys():
            property = object[p]
            property_url = object_url + '/' + Properties[p] #look up number string for this property
            for i in property.keys(): #array index
                array_url = property_url + '/' + i
                property[i]['__link__'] = array_url
            property['__link__'] = property_url            
        object['__link__'] = object_url
    device['__link__'] = device_url


Objects = {
        "AnalogInput"   :   '0',
        "AnalogOutput"  :   '1',
        "AnalogValue"   :   '2',
        "BinaryInput"   :   '3',
        "BinaryOutput"  :   '4',
        "BinaryValue"   :   '5',
        "Calendar"      :   '6',
        "Command"       :   '7',
        "Device"        :   '8',
    }

property_ids = {
        0 : 'Acked Transistions',
        1 : 'Ack Required',
        2 : 'Action',
        3 : 'Action Text',
        4 : 'Active Text',
        5 : 'Active VT Sessions',
        6 : 'Alarm Value',
        7 : 'Alarm Values',
        8 : 'All',
        9 : 'All Writes Successful',
        10 : 'APDU Segment Timeout',
        11 : 'APDU Timeout',
        12 : 'Application Software Revision',
        13 : 'Archive',
        14 : 'Bias',
        15 : 'Change Of State Count',
        16 : 'Change Of State Time',
        17 : 'Notification Class',
        #removed properties
        19 : 'Controlled Variable Reference',
        20 : 'Controlled Variable Units',
        21 : 'Controlled Variable Value',
        22 : 'COV Increment',
        23 : 'Date List',
        24 : 'Daylight Savings Status',
        25 : 'Deadband',
        26 : 'Derivative Constant',
        27 : 'Derivative Constant Units',
        28 : 'Description',
        29 : 'Description Of Halt',
        30 : 'Device Address Binding',
        31 : 'Device Type',
        32 : 'Effective Period',
        33 : 'Elapsed Active Time',
        34 : 'Error Limit',
        35 : 'Event Enable',
        36 : 'Event State',
        37 : 'Event Type',
        38 : 'Exception Schedule',
        39 : 'Fault Values',
        40 : 'Feedback Value',
        41 : 'File Access Method',
        42 : 'File Size',
        43 : 'File Type',
        44 : 'Firmware Revision',
        45 : 'High Limit',
        46 : 'Inactive Text',
        47 : 'In Process',
        48 : 'InstanceOf',
        49 : 'Integral Constant',
        50 : 'Integral Constant Units',
        51 : 'Issue Confirmed Notifications',
        52 : 'Limit Enable',
        53 : 'List Of Group Members',
        54 : 'List Of Object Property References',
        55 : 'List of Session Keys',
        56 : 'Local Date',
        57 : 'Local Time',
        58 : 'Location',
        59 : 'Low Limit',
        60 : 'Manipulated Variable Reference',
        61 : 'Maximum Output',
        62 : 'Max Message Length Supported',
        63 : 'Max Info Frames',
        64 : 'Max Master',
        65 : 'Maximum Present Value',
        66 : 'Minimum Off Time',
        67 : 'Minimum On Time',
        68 : 'Minimum Output',
        69 : 'Minimum Present Value',
        70 : 'Model Name',
        71 : 'Modification Date',
        72 : 'Notify Type',
        73 : 'Number of APDU Retries',
        74 : 'Number Of States',
        75 : 'Object Identifier',
        76 : 'Object List',
        77 : 'Object Name',
        78 : 'Object Property Reference',
        79 : 'Object Type',
        80 : 'Optional',
        81 : 'Out Of Service',
        82 : 'Output Units',
        #see event parameters
        84 : 'Polarity',
        85 : 'Present Value',
        86 : 'Priority',
        87 : 'Priority Array',
        88 : 'Priority For Writing',
        89 : 'Process Identifier',
        90 : 'Priority Array',
        91 : 'Program Location',
        92 : 'Program State',
        93 : 'Proportional Constant',
        94 : 'Proportional Constant Units',
        95 : 'Protocol Conformance Class',
        96 : 'Protocol Object Types Supported',
        97 : 'Protocol Services Supported',
        98 : 'Protocol Version',
        99 : 'Read Only',
        100 : 'Reason For Halt',
        101 : 'Recipient',
        102 : 'Recipient List',
        103 : 'Reliability',
        104 : 'Relinquish Default',
        105 : 'Required',
        106 : 'Resolution',
        107 : 'Segmentation Supported',
        108 : 'Setpoint',
        109 : 'Setpoint Reference',
        110 : 'State Text',
        111 : 'Status Flags',
        112 : 'Mode: System Status',
        113 : 'Time Delay',
        114 : 'Time of Active Time Reset',
        115 : 'Time of State Count Reset',
        116 : 'Time Synchronization Recipients',
        117 : 'Units',
        118 : 'Update Interval',
        119 : 'UTC Offset',
        120 : 'BACnet Vendor ID',
        121 : 'Vendor Name',
        122 : 'VT Classes Supported',
        123 : 'Weekly Schedule',
        124 : 'Attempted Values',
        125 : 'Average Value',
        126 : 'Buffer Size',
        127 : 'Client COV Increment',
        128 : 'COV Resubscription Interval',
        129 : 'Current Notify Time',
        130 : 'Event Time Stamps',
        131 : 'Log Buffer',
        132 : 'Log Device Object Property',
        133 : 'Log Enable',
        134 : 'Log Interval',
        135 : 'Maximum Value',
        136 : 'Minimum Value',
        137 : 'Notification Threshold',
        138 : 'Previous Notify Time',
        139 : 'Protocol Revision',
        140 : 'Records Since Notification',
        141 : 'Record Count',
        142 : 'Start Time',
        143 : 'Stop Time',
        144 : 'Stop When Full',
        145 : 'Total Record Count',
        146 : 'Valid Samples',
        147 : 'Window Interval',
        148 : 'Window Samples',
        149 : 'Maximum Value Timestamp',
        150 : 'Minimum Value Timestamp',
        151 : 'Variance Value',
        152 : 'Active COV Subscriptions',
        153 : 'Backup Failure Timeout',
        154 : 'Configuration Files',
        155 : 'Database Revision',
        156 : 'Direct Reading',
        157 : 'Last Restore Time',
        158 : 'Maintenance Required',
        159 : 'Member Of',
        160 : 'Mode',
        161 : 'Operation Expected',
        162 : 'Setting',
        163 : 'Silenced',
        164 : 'Tracking Value',
        165 : 'Zone Members',
        166 : 'Life Safety Alarm Values',
        167 : 'Max Segments Accepted',
        168 : 'Profile Name',
}

def prepare_property_ids():
    Properties.clear()
    for k in property_ids.keys():
        prop = property_ids[k]
        Properties[string.join(prop.split(' '),'_').lower()] = str(k)

def convert_tree_to_xml(file, tree, name, bacnet_path, depth=0):
    if tree.has_key('__link__'):
        if len(tree.keys()) == 1: #is regular alias point
            s = alias_point % (name, bacnet_path + tree['__link__'])
            s = s.split('\n')
            for l in s:
                file.write('  ' * depth)
                file.write(l + '\n')
            return
        #since an alias group with a link
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
        s = alias_group_link % (bacnet_path + tree['__link__'],)
        s = s.split('\n')
        for l in s:
            file.write('  ' * depth)
            file.write(l + '\n')
        for k in tree.keys():
            if k == '__link__': continue
            convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
            file.write('  ' * (depth + 1))
            file.write(close_node)
        return
    if name is not None:
        file.write('  ' * depth)
        file.write(alias_group_header % (name,))
    for k in tree.keys():
        convert_tree_to_xml(file, tree[k], k, bacnet_path, depth+1)
        file.write('  ' * (depth + 1))
        file.write(close_node)
    return
    
def convert_file(grep_file, bacnet_path):
    f=open(grep_file)
    urls = parse_grep_file_into_list(f)

    prepare_property_ids()

    t = convert_node_urls_to_dictionary_tree(urls)
    add_links_to_tree(t)

    #take the nae xml filename and insert 'alias.' in front of it for the output file name
    path = f.name.split('/') #break apart the path name
    file_name = path.pop().split('.') #basic name
    file_name.insert(0,'alias') #make it 'alias.whatever.xml'
    path.append('.'.join(file_name)) #add changed name to any path
    result_file_name = '/'.join(path) #presto chango
    x = open(result_file_name,'w+')

    x.write(xml_header)
    x.write(alias_group_header % (carrier_name,))

    convert_tree_to_xml(x, t, None, bacnet_path)

    x.write(close_node)
    x.write('</mpxconfig>\r\n')
    x.close()
 
xml_header = "<mpxconfig node_version='1.5.0.dev.11'>\r\n"

alias_group_header = "<node name='%s' node_id='452' module='mpx.service.aliases.factory'  config_builder=''  inherant='false' description='Alias group'>\r\n"

alias_group_link = """  <config>
    <property name='__type__' value='point'/>
    <property name='node_url' value='%s'/>
  </config>"""

alias_point = """<node name='%s' node_id='257' module='mpx.service.alias.factory'  config_builder=''  inherant='false' description='Alias (another name for an existing node)'>
  <config>
    <property name='__type__' value='point'/>
    <property name='node_url' value='%s'/>
  </config>"""

close_node = "</node>\n"

if __name__ == '__main__':
    import sys
    if '-h' in sys.argv or len(sys.argv) < 2:
        print 'Generates an Alias xml snippet from an a list of Old BACnet stack URLS'
        print 'the resulting file is imported, in the config tool, under:'
        print '   /interfaces/eth#/'
        print 'URL list can be generated by the following command in a mediator:'
        print '''in /var/mpx/www run grep 'node="/interfaces/eth0/BACnet' http/* > /urls.txt'''
        print
        print 'Syntax:'
        print 'bacnet_aliaes file_of_urls [--bacnet_path path_to_Devices]'
    else:
        bacnet_path = '/services/network/BACnet/internetwork/Devices/'
        if '--bacnet_path' in sys.argv:
            bacnet_path = sys.argv[sys.argv.find('--bacnet_path')+1]
        nae_file = sys.argv[1]
        convert_file( nae_file, bacnet_path )


