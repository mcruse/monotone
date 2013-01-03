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
import types, time, array, struct, urllib as _urllib, os, StringIO, threading as _threading
from mpx import properties
from mpx.lib import msglog, urllib, threading, sgml_formatter, socket, EnumeratedDictionary
from mpx.lib.exceptions import ENoSuchName, ETimeout
from mpx.lib.node import CompositeNode
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.configure import set_attribute, get_attribute
from mpx.lib.persistent import PersistentDataObject
from mpx.lib import datetime
from mpx.lib.scheduler import scheduler
from mpx.lib.node import as_node
from xml import sax
from mpx.precor.node import _xml, session_data_formatter
from mpx.lib.aerocomm import aero
from mpx.ion.aerocomm import aerocomm, csafe, feu

class LocalView(CompositeNode, AutoDiscoveredNode):
    def __init__(self):
        CompositeNode.__init__(self)
        AutoDiscoveredNode.__init__(self)
        self._children_have_been_discovered = 0
        self.enable_local_view = 1
        self.debug = 1
        self._running = 0
        self._aero_server_node = None
        return
    def configure(self, cd):
        cd['name'] = 'Local_View' # get rid of any numeric suffixes added during CompositeNode.configure()
        CompositeNode.configure(self, cd)
        set_attribute(self,'enable_local_view', self.enable_local_view, cd, int) #true to discover and start local view service
        return
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self,'enable_local_view',cd,int)  # max num instances of Alarm allowed in cur AlarmsMsg object's list
        get_attribute(self,'__node_id__',cd,str)
        return cd

    def _discover_children(self):
        if self.enable_local_view and self._running: #and not self._children_have_been_discovered: #empty
            if self.debug: print 'LocalView discover children'
            self._children_have_been_discovered = 1
            answer = {}
            existing_names = self.children_names(auto_discover=0)
            #get the remote transceiver node names from parents aerocomm server
            active_xcvr_names = self._remote_transceiver_names()
            if self.debug: print 'active names=', active_xcvr_names
            parents_configured_names = self._parents_names()
            if self.debug: print 'configured names=', parents_configured_names
            new_names = {}
            for n in active_xcvr_names:
               new_names[n]=n
            for n in parents_configured_names:
               new_names[n]=n
            for n in new_names.keys():  #add all discovered and configured devices to children list
               if n not in existing_names:
                  if self.debug: print 'add FeuSummaryNode named:', n
                  answer[n] = FeuSummaryNode()
            return answer
        return self._nascent_children
    def _remote_transceiver_names(self):
        answer = []
        devices = self._aero_server_node.get_devices()
        for d in devices:
            answer.append(str(d).replace(':','_'))
        return answer
    def _parents_names(self):
        answer = []
        devices = self.parent._ics_conf.get_units_map().keys()
        for d in devices:
            answer.append(str(d).replace(':','_'))
        return answer

    def start(self):
        self._aero_server_node = self.parent._aero_server_node
        CompositeNode.start(self)
        self._running = 1
        return

    def stop(self):
        self._running = 0
        ##
        # @todo Remove auto-created nodes (eg logger, aeroserver, etc.),
        # to prevent "Already Exists" errors at next call on start(). OR
        # simply check for node pre-existence during start. Reconfig if
        # nodes already exist.
        #
        CompositeNode.stop(self)
        return
    def get(self, skipCache=0):
        return ['<b>FEU Status</b>','<b>Xcvr Status</b>','<b>Error Code</b>','<b>Manufacturer</b>','<b>Product Category</b>',
                '<b>Model Type</b>','<b>Radio ID</b>','<b>Current Speed</b>','<b>Current Incline</b>',
                '<b>Current Course</b>','<b>Current Resistance</b>']
        #removed '<b>Unit Identifier</b>', from just prior to '<b>Radio ID</b>'

class FeuSummaryNode(CompositeNode):
    def __init__(self):
        CompositeNode.__init__(self)
        self.feu = None
    #answer the HTML for one line in the 
    def get(self, skipCache=0):
        try:
            if self.feu is None: #need to locate our feu
                if self.debug: print 'get feu for: ', self.name
                self.xcvr = self.parent._aero_server_node.get_child(self.name)
                feu = self.xcvr.get_child('FEU')
                self._feu_version_node = feu.get_child('Version')
                self._feu_error_node = feu.get_child('Error_Code')
                self._feu_status_node = feu.get_child('Status')
                self._feu_description_node = feu.get_child('description')
                self._feu_speed_node = feu.get_child('Speed')
                self._feu_grade_node = feu.get_child('Grade')
                self._feu_program_node = feu.get_child('Program')
                self._feu_gear_node = feu.get_child('Gear')
                self.feu = feu
                if self.debug: print 'get feu done'
    
            self._xcvr_status = self.xcvr.get()
            self.version_status = self._feu_version_node.get()
    
            answer =  []
            answer.append(self.feu_status())
            answer.append(str(self.xcvr_status()))
            answer.append(self.feu_error_code())
            answer.append(self.feu_manufacturer())
            answer.append(self.feu_catagory())
            answer.append(self.feu_model())
            #answer.append(self.feu_description())
            answer.append(self.feu_radio_id())
            answer.append(self.feu_speed())
            answer.append(self.feu_grade())
            answer.append(self.feu_program())
            answer.append(self.feu_gear())
            #print answer
            return answer
        except:
            msglog.exception()
            return ['-','-','-','-','-','-','-','-','-','-','-','-']

    def feu_status(self):
        v = self._feu_status_node.get()
        if v is None:
            v = 100
        else:
            v = int(v)
        if (self._xcvr_status == 2) and (v in status_spot_table.keys()):
            img = status_spot_table[v]
        else:
            img = status_spot_table[100]
        answer = '<a ref="/nodebrowser%s">' % (self.feu.as_node_url())
        answer += '<img src="' + img + '"></a>'
        return answer
    def feu_error_code(self):
        value = self._feu_error_node.get()
        if value is None:
            return '-'
        if value == 255:
            return '-'
        return str(value)
    def feu_manufacturer(self):
        vs = self.version_status
        if vs is None:
            return '????'
        try:
            man = vs.manufacturer
            if man == 1:
                return 'Precor'
            return str(man) #other manufacturers return numeric value
        except:
            return '???'
    def feu_model(self):
        vs = self.version_status
        if vs is None:
            return '????'
        try:
            try:
                return mnt[vs.model][0]
            except:
                return str(vs.model) #get fancy later
        except:
            return '???'
    def feu_catagory(self):
        try:
            try:
                return model_type_table[mnt[self.version_status.model][1]]
            except:
                return str(self.version_status.model)
        except:
            return '????'
    def feu_description(self):
        answer = self._feu_description_node.get()
        if answer is None:
            return '-'
        return answer
    def feu_radio_id(self):
        try:
            return str(self.xcvr.mac_address)
        except:
            return '????'
    def feu_speed(self):
        try:
            speed = self._feu_speed_node.get()
            return feu_both(speed, speed_conv_table)
        except:
            return '????'
    def feu_grade(self):
        try:
            speed = self._feu_grade_node.get()
            return feu_both(speed, incline_conv_table)
        except:
            return '????'
    def feu_program(self): #aka course
        try:
            program = self._feu_program_node.get()
            try:
                course_num = program.program
                level = program.level
                model_num = self.version_status.model
                return model_courses_table[mnt[model_num][2]][course_num]  #try and find in table
            except:
                return str(program.program)  #return raw data otherwise
        except:
            return '-'
    def feu_gear(self): #aka resistance
        try: 
            if mnt[self.version_status.model][1] == 0: #treadmill
                return 'n/a'
            resistance = self._feu_gear_node.get()
            if resistance:
                return str(resistance)
        except:
            pass
        return '-'
    def xcvr_status(self):
        return TransceiverState[int(self._xcvr_status)]

TransceiverState = EnumeratedDictionary({ 
    0:'stopped',
    1:'not responding',
    2:'responding',
    3:'exception in xmit'
    })

## Map of model index number to model data. Model data array = [name,category,courses_table]:

## These tables will be downloaded as part of the configuration eventually

#model number:[name,catagory,course_table_index]
mnt = {0:["C964 (0)",0,0],3:["C764 (3)",1,0],5:["C964i (5)",0,1],7:["C966 (7)",0,2],16:["C846 (16)",3,9],
    17:["C846 (17)",3,9],40:["EFX556 (40)",2,3],46:["C956 (46)",0,2],47:["C954 (47)",0,4],48:["EFX546 (48)",2,5],
    60:["C934 (60)",0,6],64:["EFX534 (64)",2,7],66:["EFX524 (66)",2,8],67:["EFX556 (67)",2,3],68:["EFX546 (68)",2,5],
    69:["C846 (69)",3,9],82:["EFX544 (82)",2,10],83:["EFX546 (83)",2,5],87:["C954 (87)",0,4],88:["C934 (88)",0,6],
    93:["C956 (93)",0,11],94:["C966 (94)",0,11],95:["EFX546 (95)",2,5],96:["EFX556 (96)",2,3]} 


## Map of model category number to model category name:
#key from mnt table value, second item
model_type_table = {0:"Treadmill",1:"Climber",2:"Elliptical",3:"Cycle"}

##Map of local ID # to course name dictionary:
model_courses_table = {
    0:{0:"manual",1:"program 1",2:"program 2",3:"program 3",4:"program 4",5:"program 5",
        6:"program 6",7:"program 7",8:"program 8",9:"program 9",10:"program 10",11:"custom 1",12:"custom 2",
        13:"interval",14:"random"},
    1:{0:"manual",1:"program 1",2:"program 2",3:"program 3",4:"program 4",5:"program 5",
        6:"program 6",7:"program 7",8:"program 8",9:"program 9",10:"program 10",11:"custom 1",12:"custom 2",
        13:"interval",14:"random",15:"heart rate control",16:"weight loss"},
    2:{0:"manual",1:"track",2:"cross country 1",3:"cross country 2",4:"cross country 3",5:"aerobic 1",
        6:"aerobic 2",7:"aerobic 3",8:"gluteal",9:"gluteal interval",10:"escalating interval",11:"1-1 interval 1",
        12:"1-2 interval",13:"1-3 interval",14:"custom 1",15:"custom 2",16:"random",17:"heart rate control",
        18:"weight loss",19:"distance goal",20:"calories goal"},
    3:{0:"manual",1:"cross training",2:"cross country",3:"hill climb",4:"interval",5:"weight loss"},
    4:{0:"manual"},
    5:{0:"manual",1:"cross training 1",2:"cross training 2",3:"cross training 3",4:"gluteal 1",5:"gluteal 2",
        6:"interval",7:"weight loss"},
    6:{0:"manual",1:"cross country",2:"interval",3:"random",4:"weight loss",5:"heart rate control"},
    7:{0:"manual",1:"hill climb",2:"interval",3:"cross training",4:"weight loss"},
    8:{0:"manual",1:"gluteal",2:"interval",3:"cross training",4:"weight loss"},
    9:{0:"manual",1:"cross country",2:"hill",3:"random",4:"1-1 interval",5:"1-2 interval",
        6:"1-3 interval",7:"watts control",8:"heart rate control",9:"weight loss",10:"resistance",11:"distance goal",
        12:"calories goal",13:"fitness test"},
    10:{0:"manual",1:"cross country 1",2:"cross country 2",3:"hill climb 1",4:"hill climb 2",
        5:"interval",6:"up/down hill",7:"valley 1",8:"valley 2"},
    11:{0:"manual",1:"track",2:"cross country 1",3:"cross country 2",4:"cross country 3",5:"5K",
        6:"aerobic 1",7:"aerobic 2",8:"gluteal",9:"gluteal interval",10:"escalating interval",11:"1-1 interval 1",
        12:"1-2 interval",13:"1-3 interval",14:"custom 1",15:"custom 2",16:"random",17:"heart rate control",
        18:"weight loss",19:"distance goal",20:"calories goal"}
    }

## Map of FEU Status Spot Images:
status_spot_table = {0:"images/Error.png",
                     1:"images/Ready.png",
                     9:"images/OffLine.png",
                     100:"images/NotResponding.png"}
      
      
      
## Map of Speed conversions:
speed_conv_table = {16:[0,1,"mph"],17:[0,0.1,"mph"],18:[0,0.01,"mph"],19:[0,0.0113636,"mph"],
    48:[0,1,"kph"],49:[0,0.1,"kph"],50:[0,0.01,"kph"],51:[0,0.06,"kph"],
    55:[1,60,"mph"],56:[1,60,"kph"],57:[1,3600,"kph"],58:[1,3600,"mph"],79:[0,0.1,"flrs/min"],
    80:[0,1,"flrs/min"],81:[0,1,"steps/min"],82:[0,1,"rpm"],83:[0,1,"str/min"],
    84:[0,1,"strks/min"],85:[0,1,"bpm"]}

## Map of Incline conversions:
incline_conv_table = {74:[0,1,"%"],75:[0,0.01,"%"],76:[0,0.1,"%"]}
      
def feu_both(v, table):
    try:
        if v is None:
            return '-'
        mag = int(v)
        given_units = int(v.units) #str of an int
        params = table[given_units]  #if it doesn't exist, throw exception
        normalized_mag = 0.0
        new_units = params[2]
        if params[0] == 0:
            normalized_mag = params[1] * mag;
        else:
            normalized_mag = params[1] / mag;
        return ('%6.2f ' % normalized_mag) + new_units
    except:
         msglog.exception()
         return str(v)
      
      
      
      
      
      
      
      
      
      
      