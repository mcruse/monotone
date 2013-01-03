"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
#!/usr/bin/env python2.2
#read in a xpoints.net file and generete a bacnet server object xml snippet

rznp = '/interfaces/com%d/rznet_peer'
xml_header = """<mpxconfig node_version='1.5.0.dev.11'>
  <node name='device address goes here' node_id='0638fbf2-8b88-4586-83fb-419eb385f60f' module='mpx.service.network.bacnet.BIN.ServerDevice'  config_builder=''  inherant='false' description='BACnet Server Device'>
    <config>
      <property name='__type__' value='point'/>
      <property name='debug' value='0'/>
      <property name='network' value='1'/>
    </config>
    <node name='8' node_id='43250856-198b-4d61-b5ed-c76fe4692d3a' module='mpx.service.network.bacnet.BIN.ServerObjectTypeGroup'  config_builder=''  inherant='true' description='Device Properties Group'>
      <config>
        <property name='__type__' value='point'/>
        <property name='debug' value='0'/>
      </config>
      <node name='device address goes here' node_id='d067ead8-ea3e-47e5-bcdb-522de0d528da' module='mpx.service.network.bacnet.BIN.ServerObjectInstance'  config_builder=''  inherant='false' description='Bacnet Device Object Instance'>
        <config>
          <property name='__type__' value='point'/>
          <property name='debug' value='0'/>
        </config>
        <node name='10' node_id='ca7c2475-e938-43b5-8ff0-1cdc3d619ee4' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='APDU Segment Timeout'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='2000'/>
          </config>
        </node>
        <node name='107' node_id='83b3429a-726d-49b1-a9a7-c7c95dde6af1' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Segmentation Supported'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='11' node_id='71e01c9d-84ca-45df-91fb-157ea4a34911' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='APDU Timeout'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='4000'/>
          </config>
        </node>
        <node name='112' node_id='5ba82b79-2a0d-4217-8024-9c96f95cfb54' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='System Status'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='12' node_id='63f472a9-fac7-4c47-a853-74ec499bd2a6' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Application Software Revision'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='1.4.52'/>
          </config>
        </node>
        <node name='120' node_id='7fa473a1-ad5a-414c-8759-8be87f73786f' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='BACnet Vendor ID'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='95'/>
          </config>
        </node>
        <node name='121' node_id='b02673c2-e814-461d-97bf-ab7980b9950c' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Vendor Name'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='Richards-Zeta'/>
          </config>
        </node>
        <node name='44' node_id='9bb2d2d0-2501-4866-be3a-338285e29639' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Firmware revision'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='3.0'/>
          </config>
        </node>
        <node name='62' node_id='c6fd2f86-290d-4d48-85aa-82795f4210bd' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Max Message Length Supported'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='1497'/>
          </config>
        </node>
        <node name='70' node_id='e4944c56-8c33-460a-9c84-d4e9656f0956' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Model Name'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='mediator'/>
          </config>
        </node>
        <node name='73' node_id='f7e0ed32-d6da-4455-b41d-417140a85df6' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Number of APDU Retries'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='3'/>
          </config>
        </node>
        <node name='75' node_id='272efdd6-cf3a-40db-a24a-9ed119cab3aa' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Object Indentifier instance (automatic)'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='76' node_id='19f1ef7f-6ec5-40d0-8aea-a3183b901f62' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Object List'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='77' node_id='dd127541-89ac-4529-b1ea-191bd24e2a3b' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Name Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='mediator'/>
          </config>
        </node>
        <node name='79' node_id='7b9c8eed-d301-423e-a620-718abef167ff' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Object Type'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='8'/>
          </config>
        </node>
        <node name='96' node_id='eb82813d-ff18-45a0-a496-f8d90c7de51c' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Protocol Object Types Supported'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='97' node_id='c839893c-c654-47db-abb9-ea63e0097858' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Protocol Services Supported'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='98' node_id='e31443a1-35ba-43ce-939f-c731dcfa9f5c' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Protocol Version'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
      </node>
    </node>
    <node name='2' node_id='5a1b5786-dd3d-48df-83af-73a3ede5b19f' module='mpx.service.network.bacnet.BIN.ServerObjectTypeGroup'  config_builder=''  inherant='false' description='Bacnet Analog Value Objects Type Group'>
      <config>
        <property name='__type__' value='point'/>
        <property name='debug' value='0'/>
      </config>
"""
xml_footer = """    </node>
  </node>
</mpxconfig>
"""
xml_point = """      <node name='%d' node_id='4d3f686c-844d-4ba6-ade0-75e385553302' module='mpx.service.network.bacnet.BIN.ServerObjectInstance'  config_builder=''  inherant='false' description='Bacnet Analog Value Object Instance'>
        <config>
          <property name='__type__' value='point'/>
          <property name='debug' value='0'/>
          <property name='link' value='%s'/>
        </config>
        <node name='36' node_id='fb147511-0e2a-4cd6-a2c1-ea56d9c8b66c' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Event State Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='75' node_id='272efdd6-cf3a-40db-a24a-9ed119cab3aa' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Object Indentifier instance (automatic)'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='77' node_id='dd127541-89ac-4529-b1ea-191bd24e2a3b' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Name Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='%s'/>
          </config>
        </node>
        <node name='79' node_id='e8552284-adfb-4a04-8424-224bd742d8a2' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Object Type (automatic)'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='81' node_id='04bad348-4bda-42d2-9819-f1447f879008' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Out Of Service Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='85' node_id='0c46d166-4d7c-4257-a0e9-5699a0c80051' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Present Value Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='87' node_id='5c13a174-cfea-4ace-a09f-9d876d1bfd02' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='false' description='Priority Array'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='104' node_id='3bc84f23-fccd-413d-b384-b5c927835afe' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='false' description='Reliquish Default Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='111' node_id='c64c3cfa-3cdf-4cb0-8a64-68c42afdf40a' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Status Flags Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
          </config>
        </node>
        <node name='117' node_id='4657bf15-fbcd-447a-936d-2e6be050d9f3' module='mpx.service.network.bacnet.BIN.ServerPropertyInstance'  config_builder=''  inherant='true' description='Units Property'>
          <config>
            <property name='__type__' value='point'/>
            <property name='debug' value='0'/>
            <property name='value' value='95'/>
          </config>
        </node>
      </node>
"""
def translate_file(xpointsfile, port):

    f = open(xpointsfile)
    x = open(xpointsfile + '.xml','w+')  #lazy, I know.

    print f
    print x

    rznps = rznp % (int(port),)

    #skip input file until we find [points] section
    while 1:
        l = f.readline()
        if len(l) == 0:
            break
        if l.find('[points]') > -1:
            break
    
    x.write(xml_header)
    point = 0
    while 1:
        try:
            l = f.readline()
            if len(l) == 0:
                break
            if l.find('=') > -1:
                point += 1
                s = l.split('=')[0]
                p = s[s.find('.'):].replace('.', '/')
                n = ':'.join(s.split('.')[2:])
                print s
                x.write(xml_point % (point, rznps+p, n))
        except:
            print 'exception'
            
    print 'Number of points written: ', point

    x.write(xml_footer)
    x.close()
    f.close()

if __name__ == '__main__':
    import sys
    if '-h' in sys.argv or len(sys.argv) < 3:
        print 'Generates BACnet proxy broadway xml snippet from RZ xpoints file'
        print 'resulting file is imported, in the config tool, under:'
        print '   /services/network/BACnet/internetwork/Devices'
        print 'Server Device name must be set to a number.'
        print 'Device Properties node, under group "8", must also be set to the same number'
        print 'All RZ points are set up as Analog Value objects (under group "2")'
        print 'Syntax:'
        print 'proxy_xpoints xpointsfile com_port_number'
    else:
        xpointsfile = sys.argv[1]
        port = sys.argv[2]
        translate_file( xpointsfile, port )
