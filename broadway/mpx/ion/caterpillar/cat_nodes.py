"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
import time
import string
import array, struct, types
from mpx.lib import msglog
from mpx.lib.node import CompositeNode
from mpx.lib.configure import set_attribute, get_attribute, \
     REQUIRED
from mpx.lib.configure import as_onoff, as_boolean, as_yesno

from mpx.lib.exceptions import ETimeout, MpxException

from mpx.lib.caterpillar import cat_lib

debug = 0

#"""
#Caterpillar Customer Communication Module (CCM)

#It is assumed the user is familiar with the Caterpillar document SEB6874-04 which 
#describes the Operation and Maintainance of the CCM.

#Connection: RS-232 9600 baud N81 on any available MPX port.

#This line handler consists of a Protocol node which holds children nodes
#which represent the CCM module itself and any Engine (Genset) controllers the CCM
#connects to.  The CCM module node is an inherent child of the protocol node 
#and serves mostly to provide status info on the connection. 

#The Protocol node has an attribute for a password used for login to the CCM.
#Usually this will be blank.  

#The Genset nodes contain children for individual parameter nodes and broadcast list nodes.
#The Genset node is configured with an attribute indicating the Module ID (MID) for the device.
#The available values are 0x58 - 0x5F.  This allows up to eight Gensets to be controlled at a
#time.  Other MID's can be added to the config tool nodedefs if need be.

#The Parameter nodes allow access to individual Parameters ID (PID) values.  Currently only read
#support is allowed.  The configuration attributes are the PID, (which must be entered in a
#hexadecimal format, ei: 0xF012 or 0x0044), a format string which follows the python "struct"
#unpacking rules, a TTL value (in float seconds) to control a timed cache for each parameter to 
#prevent unnecessary reads of the point and a list of individual properties which may be encoded 
#into the parameter value.

#PID:  In the manual for the CCM, each parameter has a description giving a PID number in
#the form of $00 $40 (for rpm) or $00 $80 (for device ID code).  These PIDs are configured
#in the config tool as 0x0040 or 0x0080 respectively.

#Format: See the python documentation for the struct module's format string info.  The
#CCM manual gives the format of the data response of parameter read as "a", "aa" or "aabbcc"
#to indicate the way values are packed into the response.  Most of the parameters simply use
#"aa" to indicate a sixteen bit integer.  Most data is sent Big endian but there are exceptions.

#Examples:  
    #PID        ccm     format
    #PID 0x0040 "aa" = ">H"  (typical)
    #PID 0xF013 "a"  = "B"
    #PID 0xF814 "aaaaaaaaaa" = 10s
    #PID 0x0080 "aabbcc" = "<HHH" (note LSB order of data bytes)
    
#If the format unpacks into more than a single value, a dictionary is used to allow access to 
#each individual value, called a property.  If the "properties" attribute contains a comma delimted
#string of words, the dictionary keys will be the words of the string split apart at the commas.

#Example:  PID 0x0080 decodes into three properties: 

#properties: Module ID,Service Tool Support Change Level,Application Type

#The result of a get will be:
    
#{'Application Type': 96, 'Module ID': 88, 'Service Tool Support Change Level': 16}

#the individual values can be split apart into nodes as outlined in the next section.
    
#Parameter Properties:  Some PIDs have complex or structured data.  These types can be decoded
#into individual nodes by this use of the properties attribute and adding child "Caterpillar
#Parameter Properties" nodes as children where the name of the node exactly matches one of the
#names given in the "properties" attribute.

#BroadcastLists are collections of PIDs that are periodically sent, unsolicited, from the 
#CCM to the MPX.  The configuration attributes are the update rate (.5 sec resolution), and
#a list number (which MUST be unique within a given CCM network).  A list can contain up to 
#eight child parameter nodes and there can be up to eight lists.  See the manual for additional
#caveats on capacity.  The PID's used for the children Parameter nodes can ONLY be the eight
#bit or sixteen bit types.  Other, larger PID types will cause the list to fail.  

#The result of a get() on the BroadcastList node will be a dictionary with the names and values
#of the child BroadcastListParameter nodes.

#Example:  broadcast_list_1  = {'coolant temp': 93, 'battery voltage': 48, 'rpm': 3600}

#The individual values are available from the chid nodes.

#Until the first update is received, the broadcast list element values will be None.

    
    
#"""

class CCM(CompositeNode):
    def __init__ (self):
        CompositeNode.__init__(self)
        self.port = None
        self.line_handler = None
        self.broadcast_lists = {}

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'password', '', config, str)
        #set_attribute(self, 'security_level', REQUIRED, config)
        #set_attribute(self, 'password_enable', REQUIRED, config)
        set_attribute(self, 'timeout', 2, config, int)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'password', config)
        #get_attribute(self, 'security_level', config)
        #get_attribute(self, 'password_enable', config)
        get_attribute(self, 'timeout', config, str)
        return config

    def start(self):
        self.port = self.parent
        if not self.port.is_open():
            self.port.open()
        self.line_handler = cat_lib.CCMLineHandler(self.port)
        self.line_handler.start(self.password)
        CompositeNode.start(self)

    def stop(self):
        if self.line_handler:
            self.line_handler.stop()
        CompositeNode.stop(self)

    #def get(self):
        #return len(self.children_nodes())

class GeneratorSet(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.description = 'Unknown'

    def configure(self, config):
        CompositeNode.configure(self, config)
        #set_attribute(self, 'number', REQUIRED, config)
        set_attribute(self, 'MID', REQUIRED, config)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        #get_attribute(self, 'number', config)
        get_attribute(self, 'MID', config)
        get_attribute(self, 'description', config)
        return config

    #def get(self):
        #return 'genset'  #engine running status

class BroadcastList(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.parameters = {}
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'update_rate', 60.0, config, float)
        set_attribute(self, 'list_number', REQUIRED, config, int)
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'update_rate', config, float)
        get_attribute(self, 'list_number', config, int)
        return config

    def start(self):
        self.line_handler = self.parent.parent.line_handler #pass it down
        self.parameters = {}
        CompositeNode.start(self)  #do children first so they register with us
        #collect list of children and create broadcast list
        self.broadcast_list = self.parameters.keys()  #set the order of the request
        index = 0 #assign an index number to each parameter and cross index
        for p in self.broadcast_list:
            self.parameters[p] = index
            index += 1
        return

    def get(self, skipCache=0): #answer a dictionary of the children's values
        answer = {}
        for n in self.children_nodes():
            if n.__class__ == BroadcastListParameter:
                answer[n.name] = n.get()
        return answer

    def register_pid(self, pid): #create cross reference for pids
        self.parameters[pid] = None
        
    def _create_and_activate_broadcast_list(self):
        self.line_handler._login()
        self.line_handler.create_broadcast_list(self.list_number, self.parent.MID, self.update_rate * 2, self.broadcast_list)
        self.line_handler.activate_broadcast_list(self.list_number)
        
    def _get_last_value_for(self, pid):
        if not self.line_handler.broadcast_lists.has_key(self.list_number):
            self._create_and_activate_broadcast_list()
        last_response = self.line_handler.broadcast_lists[self.list_number]
        index = self.parameters[pid] * 3 + 7
        if last_response:
            return struct.unpack('>H', last_response[index:index+2])[0]
        return None

class BroadcastListParameter(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.description = 'Unknown'
        self.scale = 1.0

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'PID', REQUIRED, config)
        set_attribute(self, 'scale', self.scale, config, float)
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'PID', config)
        get_attribute(self, 'scale', config, float)
        return config

    def start(self):
        self.parent.register_pid(self.PID)  #register with parent
        CompositeNode.start(self)
        
    def get(self, skipCache=0):
        answer = self.parent._get_last_value_for(self.PID)
        if answer:  #protect against None last_value
           answer = answer * self.scale
        return answer

class Parameter(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.description = 'Unknown'
        self.format = 'B'
        self.security_level = 0
        self.properties = ''
        self.ttl = 2.0
        self.last_time_stamp = time.time()
        self.last_response = None
        self.property_values = {}
        self.scale = 1.0

    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'PID', REQUIRED, config, str)
        set_attribute(self, 'description', self.description, config, str)
        set_attribute(self, 'format', REQUIRED, config, str)
        set_attribute(self, 'properties', self.properties, config, str)
        set_attribute(self, 'ttl', self.ttl, config, float)
        set_attribute(self, 'scale', self.scale, config, float)
        
    
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'PID', config)
        get_attribute(self, 'description', config)
        get_attribute(self, 'format', config)
        get_attribute(self, 'properties', config)
        get_attribute(self, 'ttl', config, int)
        get_attribute(self, 'last_response', config, repr)
        get_attribute(self, 'scale', config, float)
        return config

    def start(self):
        self.port = self.parent.parent.port #pass it down
        self.line_handler = self.parent.parent.line_handler
        if cat_lib.is_writeable(self.PID):
            self.set = self._set
        pid = cat_lib._hex_str_2_int(self.PID)
        if cat_lib.PID.has_key(pid):
            self.description, self.security_level, self.conversion, self.propattrs = cat_lib.PID[pid]
        CompositeNode.start(self)
        return

    def get(self, skipCache=0):
        now = time.time()
        if now > self.last_time_stamp + self.ttl:
            self.last_response = self.line_handler.read_single_parameter(self.parent.MID, self.PID)
            self.last_time_stamp = now
            
        response = self.last_response[7:]
        try:
            values = struct.unpack(self.format, response.tostring())
        except:
            msglog.log('mpx:ccm',msglog.types.ERR, 'struct unpack: %s with format: %s' % (str(response),self.format))
            msglog.exception()
            raise
        if len(values) == 1:
            answer = values[0]
            if type(answer) not in types.StringTypes:
               answer = answer * self.scale #only single value nodes get scaled
        else:
            answer = {}
            index = 0
            prop_names = self.properties.split(',')
            for v in values:  #for each value, put into dict
                if len(prop_names) > index:
                    answer[prop_names[index]] = v
                else:
                    answer['property_'+str(index)] = v
                index += 1
            self.property_values = answer
        if debug: print repr(answer)
        return answer

    def _set(self):
        self.line_handler.write_single_paremter(self.parent.MID, self.PID, self._encoded_value())
    def _encoded_value(self):
        return array.array('B')
        
class ParameterProperty(CompositeNode):

    def get(self, skipCache=0):
        return self.parent.property_values[self.name]
