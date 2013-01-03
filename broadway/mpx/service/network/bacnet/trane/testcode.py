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

from mpx.lib.node import as_node
t=as_node('/services/network/BACnet/internetwork1/Services/TSWS')
t=as_node('/services/network/BACnet/internetwork/Configuration')

t.change_hardware_settings('IP','eth0','1','47802')
t.change_hardware_settings('IP','eth0','1','47821')
t.change_hardware_settings('IP','eth0','1','47428')


from mpx.lib.node import as_node
ai1 = as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01')
aipv=as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01/present_value')
ain=as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01/object_name')
from mpx.lib.bacnet._bacnet import read_property_multiple_g3 as rpm
rpm(aipv.bacnet_property.device, [aipv.bacnet_property.property_tuple, ain.bacnet_property.property_tuple])

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
ai1 = as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01')
aipv=as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01/present_value')
ain=as_node('interfaces/eth0/BACnetIP/2/AnalogInput_01/object_name')
sid = SM.create_polled({1:aipv, 2:ain})

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
aipv=as_node('services/network/BACnet/internetwork1/Devices/1/8/1/77')
ain =as_node('services/network/BACnet/internetwork1/Devices/1/8/1/79')
pcm1=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/85')
pcm2=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/79')
up = as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10209')
mdd= as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10210')

sid = SM.create_polled({1:aipv, 2:ain, 3:pcm1, 4:pcm2, 5:up, 6:mdd})
sid = SM.create_polled({5:up,6:mdd})
SM.poll_all(sid)

SM.destroy(sid)

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
pcm1 = as_node('services/network/BACnet/internetwork1/Devices/1/8/1')
ns1 = pcm1.children_names()
cp1 = {}
for n in ns1:
    cp1[n] = pcm1.get_child(n)

sid1 = SM.create_polled(cp1)
SM.poll_changed(sid1)

pcm2 = as_node('services/network/BACnet/internetwork1/Devices/1/151/1')
ns2 = pcm2.children_names()
cp2 = {}
for n in ns2:
    cp2[n] = pcm2.get_child(n)

sid2 = SM.create_polled(cp2)
SM.poll_changed(sid2)


from mpx.lib.bacnet import property
for c in cp2.keys():
  if cp2[c].get_batch_manager():
    print c, 'ok'
  elif isinstance(cp2[c].decoder(), property._Array):
      print c, 'array'
  else:
      print c, '*******'


from mpx.lib.bacnet import property
property.debug = 0

from mpx.ion.bacnet import device
device.debug = 0

rpm(aipv.bacnet_property.device, [aipv.bacnet_property.property_tuple, ain.bacnet_property.property_tuple])

from mpx.lib.node import as_node
n=as_node('/services/network/BACnet/internetwork/Devices/6/130/5')
n.get_child('10106')



/services/network/BACnet/internetwork/Devices/6/151/4/1006

/services/network/BACnet/internetwork/Devices/6/130/5/1006

 

from mpx.lib.bacnet._bacnet import read_property_g3 as rp
from mpx.lib.bacnet._bacnet import read_property_multiple_g3 as rpm

rpm(6,[(151,4,1060,1),(151,4,1060,2),(151,4,1060,3),(151,4,1060,4),(151,4,1060,5)], 20.0)


from mpx.lib.service.

from mpx.lib.node import as_node
t=as_node('/services/network/BACnet/internetwork1/Services/TSWS')
t.change_hardware_settings('IP','eth0','1','47819')

SM.poll_all(self._proxy_sid)[1]
t.change_hardware_settings('Ethernet', 'eth0', '1', None)
t.change_hardware_settings(None, None, None, None)

from mpx.lib.node import as_node
t=as_node('/services/network/BACnet/internetwork1/Services/TSWS')
bbmd = t.get_child('BBMD')

bbmd.get_bdt_for()
bbmd.get_bdt_from(1,'10.1.1.67',47819)
bbmd.update_bbmds([('10.1.1.67', '47819', '255.255.255.255'),])

bbmd = t.get_child('BBMD')
bbmd.update_bbmds([('10.1.1.67', '47819', '255.255.255.255'),('10.4.2.3', '47819', '255.255.255.255')])
bbmd.enable_bbmd()

bbmd.update_bbmds([('10.4.2.3', '47819', '255.255.255.255'),])
bbmd.validate_bbmds([('10.1.1.67', '47819', '255.255.255.255'),('10.4.2.3', '47819', '255.255.255.255')])

bbmd.destroy_table()
bbmd.enable_bbmd()
bbmd.disable_bbmd()
i = as_node('/interfaces/eth0/BACnetIP/')

a = as_node('/services/network/BACnet/internetwork1/Devices/1/0/4/85')


tsenum1, est1 are old tables

for k in t.tsenum1.keys():
 for j in t.est1[t.tsenum1[k]].keys():
  if j in t.est[t.tsenum[k]].keys():
    if t.est1[t.tsenum1[k]][j] != t.est[t.tsenum[k]][j]:
     print k,j, repr(t.est1[t.tsenum1[k]][j]), repr(t.est[t.tsenum[k]][j])
     pass
    pass
  else:
   print k, j, repr(t.est1[t.tsenum1[k]][j]), '*** missing ***'
...

from mpx.lib.threading import Thread
from mpx.lib.node import as_node
class T(Thread):
    def __init__(self, node):
        Thread.__init__(self)
        self.node = node
    def run(self):
        try:
            answer = '%s %s' % (self.node.name, str(self.node.get(),))
            print answer
        except Exception, e:
            answer = '%s %s %s' % ('Exception: ', self.node.name, str(e))
            print answer

t=as_node('/services/network/BACnet/internetwork1/Devices/1/151/1')
ts = []
for n in t.children_nodes():
    ts.append(T(n))

for x in ts:
    x.start()







from mpx.lib.node import as_node
aipv=as_node('services/network/BACnet/internetwork1/Devices/1/8/1/77')
ain =as_node('services/network/BACnet/internetwork1/Devices/1/8/1/79')
pcm1=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/85')
pcm2=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/79')
up = as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10209')
mdd= as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10210')

ns = {1:aipv, 2:ain, 3:pcm1, 4:pcm2, 5:up, 6:mdd}
bm = aipv.get_batch_manager()
bs = bm.create_batches(ns)

bm.get_batch(bs[0])




from mpx.lib.node import as_node
a=as_node('/services/network/BACnet/internetwork1/Devices/1/132/1/1124/array')
ns={}
for c in a.children_nodes():
    ns[c.as_node_url()] = c

ns[a.parent.as_node_url()] = a.parent
bm=a.parent.get_batch_manager()
bs = bm.create_batches(ns)

bm.get_batch(bs[0])

for k in SM._SubscriptionManager__master_node_table.keys():
  if isinstance(k, int):
   print k
##
    as_node('/services/network/BACnet/internetwork/Devices/6/187/28'

SM._SubscriptionManager__prime_pool._ThreadPool__queue._q

from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
aipv=as_node('services/network/BACnet/internetwork1/Devices/1/8/1/77')
ain =as_node('services/network/BACnet/internetwork1/Devices/1/8/1/79')
pcm1=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/85')
pcm2=as_node('services/network/BACnet/internetwork1/Devices/1/151/1/79')
up = as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10209')
mdd= as_node('services/network/BACnet/internetwork1/Devices/1/151/1/10210')
xxx= as_node('services/network/BACnet/internetwork1/Devices/1/130/1/10133')
xxy= as_node('services/network/BACnet/internetwork1/Devices/1/132/1/1124')
ns = {1:aipv, 2:ain, 3:pcm1, 4:pcm2, 5:up, 6:mdd, 7:xxx, 8:xxy}
sid = SM.create_polled(ns)

SM.poll_changed(sid)


from mpx.lib.node import as_node
a={}
d=as_node('services/network/BACnet/internetwork/Devices/6/181/426/')
cn=d.children_nodes()
for n in cn:
    a[n.name]=n

sid = SM.create_polled(a)

SM.poll_all(sid)

SM.poll_changed(sid)

SM.destroy(sid)


['/services/network/BACnet/internetwork/Devices/6/181/426/13717', '/services/network/BACnet/internetwork/Devices/6/181/426/13706', '/services/network/BACnet/internetwork/Devices/6/181/426/13768', '/services/network/BACnet/internetwork/Devices/6/181/426/11342', '/services/network/BACnet/internetwork/Devices/6/181/426/13707', '/services/network/BACnet/internetwork/Devices/6/181/426/13730', '/services/network/BACnet/internetwork/Devices/6/181/426/10066', '/services/network/BACnet/internetwork/Devices/6/151/4/1052', '/services/network/BACnet/internetwork/Devices/6/181/426/13711', '/services/network/BACnet/internetwork/Devices/6/181/426/13742', '/services/network/BACnet/internetwork/Devices/6/151/4/1105', '/services/network/BACnet/internetwork/Devices/6/181/426/13767', '/services/network/BACnet/internetwork/Devices/6/151/4/1056', '/services/network/BACnet/internetwork/Devices/6/181/426/13729', '/services/network/BACnet/internetwork/Devices/6/181/426/13795', '/services/network/BACnet/internetwork/Devices/6/181/426/13733', '/services/network/BACnet/internetwork/Devices/6/181/426/13749', '/services/network/BACnet/internetwork/Devices/6/181/426/85', '/services/network/BACnet/internetwork/Devices/6/181/426/13604', '/services/network/BACnet/internetwork/Devices/6/181/426/13769', '/services/network/BACnet/internetwork/Devices/6/181/426/11341', '/services/network/BACnet/internetwork/Devices/6/181/426/13791', '/services/network/BACnet/internetwork/Devices/6/181/426/11245', '/services/network/BACnet/internetwork/Devices/6/181/426/13727', '/services/network/BACnet/internetwork/Devices/6/181/426/13710', '/services/network/BACnet/internetwork/Devices/6/181/426/13793', '/services/network/BACnet/internetwork/Devices/6/181/426/10413', '/services/network/BACnet/internetwork/Devices/6/181/426/13792', '/services/network/BACnet/internetwork/Devices/6/151/4/10210', '/services/network/BACnet/internetwork/Devices/6/181/426/13728', '/services/network/BACnet/internetwork/Devices/6/181/426/13794', '/services/network/BACnet/internetwork/Devices/6/181/426/10586', '/services/network/BACnet/internetwork/Devices/6/181/426/13770', '/services/network/BACnet/internetwork/Devices/6/181/426/13796', '/services/network/BACnet/internetwork/Devices/6/181/426/13716', '/services/network/BACnet/internetwork/Devices/6/181/426/13737', '/services/network/BACnet/internetwork/Devices/6/151/4/1112', '/services/network/BACnet/internetwork/Devices/6/181/426/13751', '/services/network/BACnet/internetwork/Devices/6/181/426/13708', '/services/network/BACnet/internetwork/Devices/6/181/426/13735', '/services/network/BACnet/internetwork/Devices/6/181/426/13709', '/services/network/BACnet/internetwork/Devices/6/181/426/11244', '/services/network/BACnet/internetwork/Devices/6/181/426/14054', '/services/network/BACnet/internetwork/Devices/6/181/426/14438', '/services/network/BACnet/internetwork/Devices/6/181/426/10585', '/services/network/BACnet/internetwork/Devices/6/181/426/13703']




"""
from mpx.lib.node import as_node
as_node('services/network/BACnet/internetwork/Configuration/IP/eth0/BBMD')

from mpx.lib.node import as_node
bbmd=as_node('/services/network/BACnet/internetwork1/Services/TSWS/BBMD')
bbmd.bbmd.get_bdt_for()
bbmd.get_bdt_from(1,'10.1.1.67',47819)
bbmd.update_bbmds([('10.1.1.67', '47819', '255.255.255.255'),('192.168.1.143','47819','255.255.255.255')])
bbmd.validate_bbmds([('10.1.1.67', '47819', '255.255.255.255'),('192.168.1.143','47819','255.255.255.255')])

"""
from mpx.service.subscription_manager._manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib.node import as_node
ns01 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/12750")
ns02 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/13741")
ns03 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/12156")
ns04 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/13712")
ns05 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/11633")
ns06 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/12747")
ns07 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/14446")
ns08 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/13715")
ns09 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/12110")
ns10 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/11447")
ns11 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/85")
ns12 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/77")
ns13 = as_node("/services/network/BACnet/internetwork/Devices/6/181/435/12296")
ns = {1:ns01, 2:ns02, 3:ns03, 4:ns04, 5:ns05, 6:ns06, 7:ns07, 8:ns08, 9:ns09, 10:ns10, 11:ns11, 12:ns12, 13:ns13}
sid=SM.create_polled(ns)

SM.poll_changed(sid)

ns14 = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/1011')

from mpx.lib.node import as_node
BOOLEAN = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10140')
BOOLEAN_array = as_node('/services/network/BACnet/internetwork/Devices/6/150/3/1051')
UNSIGNEDINT = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/120')
UNSIGNEDINT_array = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1139')
REAL = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/108')
REAL_array = as_node('/services/network/BACnet/internetwork/Devices/6/150/3/1108')
OCTET_STRING = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1129')
#OCTET_STRING_array = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/13601')
CHARSTRING = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/121')
CHARSTRING_array = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1123')
#BITSTRING = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/10102')
ENUMERATED = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/79')
ENUMERATED_array = as_node('/services/network/BACnet/internetwork/Devices/6/151/4/1106')
DATE = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/56')
TIME = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/57')
OBJECT_ID= as_node('/services/network/BACnet/internetwork/Devices/6/8/6/75')
OBJECT_ID_array = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1126')
DATE_TIME = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/1011')
BACNET_OBJ_PROP_REFERENCE = as_node('/services/network/BACnet/internetwork/Devices/6/4/17/1002')
APEX_PROP_REFERENCE = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10138')
APEX_PROP_REFERENCE_array = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1137')
APEX_OBJECT_REFERENCE = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10111')
APEX_OBJECT_REFERENCE_array = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/1006')
APEX_AREA_MEMBER_list = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10132')
APEX_TIME_EVENT_VALUE_array = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/123')
APEX_SPECIAL_EVENT = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/38')
APEX_SCHEDULE_MEMBER = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/10132')
APEX_EVENT_CLASS = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/10195')
APEX_ANALOG_LIMIT_BLOCK = as_node('/services/network/BACnet/internetwork/Devices/6/0/18/10176')
APEX_PCM_DISPLAY_PACKET = as_node('/services/network/BACnet/internetwork/Devices/6/151/4/10218')
BACNET_OBJ_TYPES_SUPPORTD = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/96')
#APEX_VAS_VOTES = as_node('/services/network/BACnet/internetwork/Devices/6/153//10412')
APEX_MODEM_STATE = as_node('/services/network/BACnet/internetwork/Devices/6/135/1/85')
APEX_MODEM_DEVICE_PHONE = as_node('/services/network/BACnet/internetwork/Devices/6/135/1/11926')
APEX_DIMENSION_PACKET = as_node('/services/network/BACnet/internetwork/Devices/6/132/1/1135')
OBJECT_CONSTANT_REAL = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10078')
OBJECT_CONSTANT_REAL_array = as_node('/services/network/BACnet/internetwork/Devices/6/151/4/10219')
OBJECT_CONSTANT_INT = as_node('/services/network/BACnet/internetwork/Devices/6/170/1/11755')
OBJECT_CONSTANT_ENUM = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10128')
OBJECT_CONSTANT_BOOL = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10116')
OBJECT_CONSTANT_BOOL_array = as_node('/services/network/BACnet/internetwork/Devices/6/151/4/10220')
#BYTESTRING2 = as_node('/services/network/BACnet/internetwork/Devices/6/8/6/13600')
APEX_CUSTOM_FIELD = as_node('/services/network/BACnet/internetwork/Devices/6/211/27/14208')
SNVT_HVAC_OVERID = as_node('/services/network/BACnet/internetwork/Devices/6/181/426')
#APPLICATION_MEMBER = as_node('/services/network/BACnet/internetwork/Devices/6/190//10132')
#SUMMIT_EXCEPTION_SCHEDULE = as_node('/services/network/BACnet/internetwork/Devices/6/208//13520')
                             
L = ['APEX_ANALOG_LIMIT_BLOCK', 'APEX_AREA_MEMBER_list', 'APEX_CUSTOM_FIELD', 'APEX_DIMENSION_PACKET', \
'APEX_EVENT_CLASS', 'APEX_MODEM_DEVICE_PHONE', 'APEX_MODEM_STATE', 'APEX_OBJECT_REFERENCE', \
'APEX_OBJECT_REFERENCE_array', 'APEX_PCM_DISPLAY_PACKET', 'APEX_PROP_REFERENCE', \
'APEX_PROP_REFERENCE_array', 'APEX_SCHEDULE_MEMBER', 'APEX_SPECIAL_EVENT', 'APEX_TIME_EVENT_VALUE_array', \
'BACNET_OBJ_PROP_REFERENCE', 'BACNET_OBJ_TYPES_SUPPORTD', 'BOOLEAN', 'BOOLEAN_array', \
'CHARSTRING', 'CHARSTRING_array', 'DATE', 'DATE_TIME', 'ENUMERATED', 'ENUMERATED_array', \
'OBJECT_CONSTANT_BOOL', 'OBJECT_CONSTANT_BOOL_array', 'OBJECT_CONSTANT_ENUM', 'OBJECT_CONSTANT_INT', \
'OBJECT_CONSTANT_REAL', 'OBJECT_CONSTANT_REAL_array', 'OBJECT_ID', 'OBJECT_ID_array', \
'OBJ_PROP_REFERENCE', 'OBJ_PROP_REFERENCE_array', 'OCTET_STRING', 'OCTET_STRING_array', \
'REAL', 'REAL_array', 'REFERENCE', 'SNVT_HVAC_OVERID', 'TIME', 'UNSIGNEDINT', 'UNSIGNEDINT_array']

for n in L:
    try:
        print n, repr(eval(n).get()._data)
    except Exception, e:
        print n, str(e)

ailb = as_node('/services/network/BACnet/internetwork/Devices/6/0/18/10176')
area = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10138')
aream = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10132')
aresp = as_node('/services/network/BACnet/internetwork/Devices/6/130/5/10078')
ao  = as_node('/services/network/BACnet/internetwork/Devices/6/1/9/1006')
tev = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/123')
tse = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/38')
tsem = as_node('/services/network/BACnet/internetwork/Devices/6/131/5/10132')
xxx = as_node('/services/network/BACnet/internetwork/Devices/6/162/1/10219')
xxxa1 = as_node('/services/network/BACnet/internetwork/Devices/6/162/1/10219/array/1')
            
             
   """  | (    *' 9 N    |  0c 28 80 00 01 1e 2a 27 eb 39 01 4e 09 01 1e 1c
  |    )  .D    /O*|  00 00 00 00 29 00 1f 2e 44 00 00 00 00 2f 4f 2a
  |' 9 N        )  |  27 eb 39 02 4e 09 01 1e 1c 00 00 00 00 29 00 1f
  |.D    /O*' 9 N  |  2e 44 00 00 00 00 2f 4f 2a 27 eb 39 03 4e 09 01
  |      )  .D    /|  1e 1c 00 00 00 00 29 00 1f 2e 44 00 00 00 00 2f
  |O*' 9 N        )|  4f 2a 27 eb 39 04 4e 09 01 1e 1c 00 00 00 00 29
  |  .D    /O*' 9 N|  00 1f 2e 44 00 00 00 00 2f 4f 2a 27 eb 39 05 4e
  |        )  .D   |  09 01 1e 1c 00 00 00 00 29 00 1f 2e 44 00 00 00
  | /O*' 9 N       |  00 2f 4f 2a 27 eb 39 06 4e 09 01 1e 1c 00 00 00
  | )  .D    /O*' 9|  00 29 00 1f 2e 44 00 00 00 00 2f 4f 2a 27 eb 39
  | N        )  .D |  07 4e 09 01 1e 1c 00 00 00 00 29 00 1f 2e 44 00
  |   /O*' 9 N     |  00 00 00 2f 4f 2a 27 eb 39 08 4e 09 01 1e 1c 00
  |   )  .D    /O  |  00 00 00 29 00 1f 2e 44 00 00 00 00 2f 4f 1f
 ...  ... """          
             