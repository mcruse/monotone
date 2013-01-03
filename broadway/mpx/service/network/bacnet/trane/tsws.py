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
from mpx.lib.node import CompositeNode, as_node
from mpx.lib.exceptions import ENoSuchName
from mpx.lib.threading import Thread
from mpx.service.network.bacnet.BIN import BIN_IP, BIN_Ethernet, BIN_MSTP, BIN_port, BIN_BBMD

from mpx.lib.bacnet._bacnet import read_trane_event_list
from mpx.lib.bacnet._bacnet import read_trane_event_log
from mpx.lib.bacnet._bacnet import acknowledge_trane_event
from mpx.lib.bacnet._bacnet import read_trane_schedule_list
from mpx.lib.bacnet._bacnet import read_trane_trend_list
from mpx.lib.bacnet._bacnet import TraneTrend
from mpx.lib.bacnet import bvlc
from mpx.lib.exceptions import *
from mpx.lib.bacnet.trane.eventlog import Trane_EventLog
from mpx.lib.scheduler import scheduler
from mpx.lib import msglog
from copy import copy
from mpx.lib.bacnet import network as _network
import time
import re
import os
import stat
import zipfile
import sqlite
import string

from HTMLParser import HTMLParser

import mpx.lib.bacnet.trane.sequence

from mpx.lib.bacnet import *
from mpx.lib.bacnet import _bacnet,sequence,trane
from mpx.lib.bacnet.data import *
import types


DEBUG = 0
DBNAME = '/var/mpx/db/authen.db'
TSWSDB = "/var/mpx/db/TSWS.db"

PA_map ={}
PA_map[1] = '1: User Emergency'
PA_map[2] = '2: Custom Programmin - No Min'
PA_map[3] = '3: Minimum On/Off'
PA_map[4] = '4: User - High'
PA_map[5] = '5: Custom Programming - High'
PA_map[6] = '6: Miscellaneous'
PA_map[7] = '7: Demand Limiting'
PA_map[8] = '8: Miscellaneous'
PA_map[9] = '9: Vav Air Systems'
PA_map[10] = '10: Chiller Plant Control'
PA_map[11] = '11: Area Control'
PA_map[12] = '12: User - Low'
PA_map[13] = '13: Miscellaneous'
PA_map[14] = '14: Timed Override'
PA_map[15] = '15: Time of Day Schedules'
PA_map[16] = '16: Custom Programming - Low'
PA_map[17] = 'xx - Relinquish Default'

_by_strings = {
    13:"Area Control",
    14:"VAS Control Server",
    15:"UCP1/TRS Control Server",
    16:"Output Control Server",
    17:"Time of Day",
    18:"CPL Control Server",
    26:"Chiller Plant Control Server"
    }


class AutoDiscovery(CompositeNode):
    def __init__(self):
        #
        # state 1 - Collecting points
        #       2 - auto-discovering points
        #       3 - completed autodiscovery
        #
        #      -1 - Error
        self.autodiscovery = {"state":0,
                              "number_of_points":0,
                              "points_discovered":0,
                              "total_time":0,
                              "start_time":0,
                              "end_time":0,
                              "percent_complete":0,
                              "number_of_files":0,
                              "files_so_far":0,
                              "used_db":False}
    def get(self,*args):
        return self.autodiscovery.copy()
    
    def _get_secs(self,s):
        if s < 10:
            rt = '0%s' % (s,)
        else:
            rt = '%s' % (s,)
        return rt
        
    def update_autodiscovery(self,state=None,
                             number_of_points=None,
                             points_discovered=None,
                             number_of_files=None, 
                             files_so_far=None,
                             used_db=None):
        if used_db != None:
            self.autodiscovery["used_db"] = used_db
            
        if state == 1:
            self.autodiscovery["percent_complete"]=0;
         
        if state != None:            
            self.autodiscovery["state"] = state
            if state == 1:
                self.autodiscovery["start_time"] = time.time()
            if state == 3:
                self.autodiscovery["end_time"] = time.time()
                tt = int(self.autodiscovery["end_time"] - self.autodiscovery["start_time"])
                if tt <60:
                    s = tt%60
                    self.autodiscovery["total_time"] =  self._get_secs(s)
                elif tt >= 60 and tt < 3600:
                    self.autodiscovery["total_time"] =  '%s:%s minutes' % (tt/60,tt%60) 
                else:
                    self.autodiscovery["total_time"] =  '%s:%s:%s hours' % (tt/3600,(tt%3600)/60,self._get_secs((tt%3600)%60)) 
        if number_of_files != None:
            self.autodiscovery['number_of_files'] = number_of_files
        
        if files_so_far != None:
            self.autodiscovery["files_so_far"] = files_so_far
            nof = self.autodiscovery['number_of_files'] 
            fsf = self.autodiscovery["files_so_far"] 
            pc = "%.2f" % (float(fsf)/float(nof)*100,)    
            # Devide by a 3 since getting the points from the file seem to take about a 1/3 the time
            self.autodiscovery["percent_complete"] = int(float(pc))/3
                
        if number_of_points != None:
            self.autodiscovery["number_of_points"] = number_of_points
            
        if points_discovered != None:    
            n = self.autodiscovery["number_of_points"]
            self.autodiscovery["points_discovered"] = points_discovered
            pc = "%.2f" % (float(points_discovered)/float(n)*100,)    
            plus =33
            if self.autodiscovery["used_db"] == True:
                self.autodiscovery["percent_complete"] = int(float(pc))
            else:
                self.autodiscovery["percent_complete"] = (int(float(pc))*2)/3 + plus
        

class Services(CompositeNode):
    _node_def_id = '0bd14bef-1c86-4cee-805a-01a7fb92f909'
    # Directories that the zip file that contains all the htm is maybe in
    web_dir = "/var/www"
    unsecure = "html"
    secure = "secure"
    trane = "trane/tsws/site"
    def __init__(self):
        CompositeNode.__init__(self)
        self._interface_node = None
        self.zip_file = None
        
    # state = 0 have not started out discovery yet
    #         1 in auto-discovery
    #         2 completed
    #         -1 Error            
    def _update_autodiscovery(self,**keywords):
        self.ad.update_autodiscovery(**keywords)
        
    def configure(self, config):
        CompositeNode.configure(self, config)
        try:
            bin_config = self.parent.parent.get_child('Configuration')
            if bin_config._get_persistent_configuration().carrier is None:
                bin_config.change_hardware_settings('IP', 'eth0', '1', '47808')
        except:
            msglog.exception()
    def change_hardware_settings(self, carrier, interface, network, port):
        try:
            if bvlc.BBMD_thread_started:
                self._interface_node = None
                bbmd = self.get_child('BBMD')
                bbmd.disable_bbmd() #no longer will pass bbmd messages
                bbmd.destroy_table() #persistent table cleared
        except ENoSuchName:
            pass
        except:
            msglog.exception()
        config_node = self.parent.parent.get_child('Configuration')
        device_node = self.parent.parent.get_child('Devices')
        dn_children = copy(device_node.children_nodes())
        #prune all the devices
        for n in dn_children:
            n.prune(1)
        device_node.stop()
        try:
            #prune the carrier node under the interface port
            if config_node.interface_node:
                intrfc_node = as_node(config_node.interface_node.node_url)
                intrfc_node.prune(1)
        except:
            msglog.exception()
        for carrier_node in config_node.children_nodes():
            for interface_node in carrier_node.children_nodes():
                try:
                    interface_node.prune()
                except:
                    msglog.exception()
        config_node.stop()
        self._interface_node = None
        config_node.change_hardware_settings(carrier, interface, network, port)
        config_node.start()
        device_node.start()
        _network._who_are_devices()
        time.sleep(3)
        self.kick_start_discovery()
    def get_hardware_settings(self):
        config_node = self.parent.parent.get_child('Configuration')
        return config_node.get_hardware_settings()

    def _set_zip_file (self):
        dir1 = os.path.join(self.web_dir,self.unsecure,self.trane)
        dir2 = os.path.join(self.web_dir,self.secure,self.trane)
        dirs = [dir1,dir2]
        self.zip_file = self.get_zip(dirs)
        
    def start(self):
        CompositeNode.start(self)
        self._set_zip_file()
        tread = Thread(name="AutoDiscovery",target=self.kick_start_discovery)
        scheduler.after(2, tread.start)
        self.ad = AutoDiscovery()
        self.ad.configure({"parent":self,"name":"AutoDiscover"})
        
    def stop(self):
        try:
            self._interface_node.stop()
        except:
            msglog.log('tsws',msglog.types.ERR,'tsws failed to stop interface node')
        self._interface_node = None
        CompositeNode.stop(self)

    def _get_mem_info(self):
        meminfo = {}
        mem_file = "/proc/meminfo"
        f = open(mem_file,'r')
        lineNum = 1
        for l in f.readlines():
            if lineNum != 1:
                m = l.split(':')  
                for x in m:
                    y = string.strip(m[1])
                    z = y.split(' ')  
                    d = {'units':z[1],'value':int(z[0])}
                    meminfo[m[0]]= d
            lineNum +=1
        return meminfo
    
    def check_mem_amount(self,numOfNodes):
        rt = True
        usedKB = 55000
        # 13kb per node
        sizePerNode = 14

        # kb size        
        memSize = (numOfNodes*sizePerNode)+usedKB

        memInfo = self._get_mem_info()
        memTotal = memInfo['MemTotal']['value']
        passed = 'PASSED'
        if memSize > memTotal:
            passed = 'FAILED'
            rt =  False
        msg = "%s Number of points:%s Estimated Memory Usage:%s kB  Total Memory:%s kB" % (passed,numOfNodes,memSize,memTotal)
        msglog.log('tsws',msglog.types.INFO,msg)
        return rt

    def kick_start_discovery(self):
        memFlag = False
        try:
            try:
                msglog.log('tsws',msglog.types.INFO,"starting auto-discovery")
                self.parent.parent.get_child('Devices').children_nodes() #kickstart the process
                self._update_autodiscovery(state=1)
                
                conn =sqlite.connect(TSWSDB)
                self.init_db(conn)
                conn.close()
                
                conn =sqlite.connect(TSWSDB)
                cur = conn.cursor()
                sql = "select node from nodes"

                cur.execute(sql)
                MAX_NODES = 50
                node_count = 0
                
                if cur.rowcount > 0:
                    if self.check_mem_amount(cur.rowcount):  
                        self._update_autodiscovery(used_db=True)
                        self._update_autodiscovery(state=2)
                        self._update_autodiscovery(number_of_points=cur.rowcount)
                        n = cur.fetchone()
                        while n:
                            node_count += 1
                            if node_count >= MAX_NODES:
                                node_count = 0
                                time.sleep(2)
                            try:
                                node = as_node(n[0])
                                node._get_aliased_node()
                                pd = self.ad.get()["points_discovered"] + 1
                                self._update_autodiscovery(points_discovered=pd)
                            except Exception,err:
                                pd = self.ad.get()["points_discovered"] + 1
                                self._update_autodiscovery(points_discovered=pd)
                                pass
                            n = cur.fetchone()
                    else:
                        msglog.log('tsws',msglog.types.INFO,"Too many Grapchis from amount of ram")
                        memFlag = True
                        self._update_autodiscovery(state=5)
                else:
                    nodes = self.collect_nodes_from_zip(conn)
                    if self.check_mem_amount(len(nodes)):
                        self._update_autodiscovery(state=2)
                        self._update_autodiscovery(number_of_points=len(nodes)) 
                        for n in nodes:
                            node_count += 1
                            if node_count == MAX_NODES:
                                node_count = 0
                                time.sleep(2)
                            try:
                                node = as_node(n)
                                node._get_aliased_node()
                                pd = self.ad.get()["points_discovered"] + 1
                                self._update_autodiscovery(points_discovered=pd)
                            except Exception,err:
                                pd = self.ad.get()["points_discovered"] + 1
                                self._update_autodiscovery(points_discovered=pd)
                                pass
                    else:
                        msglog.log('tsws',msglog.types.INFO,"To many Grapchis from amount of ram")
                        memFlag = True
                        self._update_autodiscovery(state=5)
                
            except:
                self._update_autodiscovery(state=-1)
                msglog.exception()
        finally:
            if memFlag == False:
                msglog.log('tsws',msglog.types.INFO,"auto-discovery finished")
                self._update_autodiscovery(state=3)
                
    def create_table(self,conn):
        sql = "create table nodes( id INTEGER PRIMARY KEY, node STRING)"
        conn.db.execute(sql)
        
        sql = "create table info( zip_file STRING PRIMARY KEY, mtime STRING)"
        conn.db.execute(sql)
     
        
    def init_db(self,conn):
        sql = "select * from sqlite_master"
        rows = conn.db.execute(sql)
        found_table = False
        if rows.rowcount == 0:
            self.create_table(conn)
        else:
            for r in rows.row_list:
                if r[0] == "table" and r[2] == "nodes":
                    found_table = True
                    break
            if found_table == False:
                self.create_table(conn)
            else:
                
                sql = 'select mtime from info where zip_file="%s"' % (self.zip_file,)
                r= conn.db.execute(sql)
                
                sql_mtime = ''
                mtime = os.stat(self.zip_file)[stat.ST_MTIME]

                if r.rowcount > 0:
                    sql_mtime = int(r.row_list[0][0])  
                    if sql_mtime != mtime:

                        sql = "delete from nodes"
                        conn.db.execute(sql)
                        conn.commit()
                        
                        sql = "delete from info"
                        conn.db.execute(sql)
                        conn.commit()
                        
                        sql = 'update info set mtime="%s" where zip_file="%s"' % (mtime,self.zip_file)
                        conn.db.execute(sql)
                        conn.commit()
                else:
                    sql = "delete from nodes"
                    conn.db.execute(sql)
                    conn.commit()
                    
                    sql = "delete from info"
                    conn.db.execute(sql)
                    conn.commit()
                    
                    sql = 'insert into info(zip_file,mtime) values("%s","%s")' % (self.zip_file,mtime)
                    conn.db.execute(sql)
                    conn.commit()
      
    def add_nodes(self,conn,nodes):
        try: 
            cur = conn.cursor()
            for n in nodes:
                sql = 'insert into nodes(node) values ("%s")' % (n,)
                cur.execute(sql)
            conn.commit()
        except:
            #print "Error:%s" %(err,)
            conn.rollback()    
    def collect_nodes_from_zip(self,conn):
        all_nodes = []
        if self.zip_file != None:
            zf = zipfile.ZipFile(self.zip_file)
            file_list = []
            for filename in zf.namelist():
                if len(filename[:]) > 3 and filename[-3:]=="htm":
                    file_list.append(filename)
            nof = len(file_list)
            self._update_autodiscovery(number_of_files=nof)
            for filename in file_list:
                fsf = self.ad.get()["files_so_far"] + 1
                self._update_autodiscovery(files_so_far=fsf)
                p = TSWSv2()
                p.feed(zf.read(filename))
                for n in p.nodes:
                    if n not in all_nodes:
                        all_nodes.append(n)
        self.add_nodes(conn,all_nodes)
        
        return all_nodes

    def find_zip(self,dir):
        files = os.listdir(dir)
        rt = None
        for f in files:
            x = os.path.join(dir,f)
            if f == "source_file.zip":
                return x
            elif os.path.isdir(x):
                f = self.find_zip(x)
                if f != None:
                    return f
            else:
                pass
        return None
    # 
    def get_zip(self,dirs):
        for d in dirs:
            f = self.find_zip(d)
            if f:
                return f
        return None              
        
    def locate_or_create_interface_node(self): #mimic port for local BBMD
        if self._interface_node:
            return self._interface_node
        config_node = self.parent.parent.get_child('Configuration')
        self._interface_node = config_node.interface_node.locate_or_create_interface_node()
        return self._interface_node #for bbmd
    def priority_array_status(self,nn):
        node = as_node(nn)
        rt = []
        enum_map = node.enum_string_map()
        pa = node.parent.get_child('87').get().value
        by_array = node.parent.get_child('1006').get().value
        for i in range(0,16):
            if pa[i] != None:
                a = [PA_map[i+1]]
                if enum_map:
                    a.append(enum_map[pa[i]])
                else:
                    a.append(pa[i]) 
                boid = by_array[i]                 
                if boid[1][0] == 15: #if object type of Program(15)
                    if _by_strings.has_key(boid[1][1]):
                        a.append( _by_strings[boid[1][1]])
                    else:
                        a.append('Unknown') #Cap U instead of lower case to help trouble shoot cause
                else:
                    device = node.parent.parent.parent
                    try:
                        if boid[0] is not None: #they specified an optional device
                            device = device.parent.get_child(str(boid[0][1]))
                        group = device.get_child(str(boid[1][0])) #object type goup
                        object = group.get_child(str(boid[1][1])) #object instance
                        a.append(str(object.get_child('77').get()))
                    except ENoSuchName,err:
                        try:
                            device = node.parent.parent.parent
                            group = device.get_child(str(boid[1][0])) #object type goup
                            object = group.get_child(str(boid[1][1]))
                            a.append(str(object.get_child('77').get()))
                        except:
                            a.append(str(boid))
                rt.append(a)
            else:
                rt.append([None,None,None])
        return rt

class Events(CompositeNode):
    _node_def_id = 'f3026915-b271-4500-a1eb-d51b5948fc45'
    ##
    # read the Trane EventLog object and return it to the caller
    # @return   A list of dictionaries, representing each event
    # @param    device
    # @param    instance
    def read_trane_event_log(self, device, instance):
        t = Trane_EventLog()
        result = t.read(device, instance)     
        for r in result:
            if type(r) == types.DictType:
                if r.has_key('ack') and type(r['ack']) == types.DictType:
                    if r['ack'].has_key('op'):
                        r['ack']['op'] = self._fix_op(r['ack']['op'])
        return result
    
    # lists out all Trane EventLog objects on the device.
    # @return   a list of dictionaries containing an entry for each
    #           EventLog on the system
    def read_trane_event_list(self, device):
        result = read_trane_event_list(device)
        return result
    
    def _fix_op(self,op):
        users = self._get_users()
        if re.match('Web User',op):
            n = re.findall('[0-9]+',op)
            if len(n) == 1:
                uid = int(n[0])
                user_found = 0
                for u in users:
                    if u[0] == uid:
                        user_found = 1
                        op = 'Web User %s' % (u[1],)
                        break
                if user_found == 0:
                    op = '%s Unknown User ID' % (op,)
        elif re.match('[0-9]+:[0-9]+/[0-9]+:[0-9]+',op):
            op = ''     
        return op
    def _get_users(self):
        import sqlite
        db = None
        rows = []
        try:
            db = sqlite.connect(DBNAME)
            c = db.cursor()
            sql = 'select uid,uname from users'
            c.execute(sql)
            rows = c.fetchall()
            return rows
        finally:
            if db != None and db.closed == 0:
                db.close()
    ##
    # 
    #   acknowledge the Trane EventLog object items
    #   @return   array of results [[1, {'dt': 1105739688.066879,
    #                                     'ctime':'',
    #                                     'op': 'Web User 11'}]]
    #   @param    device
    #   @param    instance
    #   @param    events [[localId, SN, DateTime],]
    def acknowledge_trane_event(self, device, instance, events, user_id):
        t = Trane_EventLog()
        result = t.acknowledge(device, instance, events, user_id)
        for r in result:
            d = r[1]
            if type(d) == types.DictType:
                if d.has_key('op'):
                    d['op'] = self._fix_op(d['op'])
        return result

class Schedules(CompositeNode):
    _node_def_id = '87699675-b55c-4b4e-8b2b-27bc9cc66eb7'
    def read_trane_schedule_list(self, device):
        return read_trane_schedule_list(device)
    ##
    # lists out all Trane-Schedule objects on the system 
    # @return a list of dictionaries containing name, device, type, and
    # instance of the trane objects on this BACnet network
    def list(self):
        scheduleList = _bacnet.read_trane_schedule_list(None)
        retList = []
        for schedule in scheduleList :
            retList.append({'name':schedule[3], 'device':schedule[0],
                             'type':schedule[1], 'instance':schedule[2]})
        return retList

    ##
    #  read the schedule object and return it to the caller
    #  @return a dictionary of lists, for time_events, schedule_members, and
    #  special_events
    #  @param  device
    #  @param  instance
    def read(self, device, instance):
        ret = {}
        effective_period = []
        time_events = []
        schedule_members = []

        #----< Build the effective period array >------------------------
        # Populate the effective start date/end date  if they exist
        result = _bacnet.read_property(device, (131, instance, 32))
        for i in range(2) :
            if result.value[2].value[i].value.month <> None :
                effective_period.append(result.value[2].value[i].value.month)
                effective_period.append(result.value[2].value[i].value.day)
                effective_period.append(result.value[2].value[i].value.year)

        # Set the effective period
        ret['effective_period'] = effective_period

        #----< Build the time events array >-----------------------------
        # Loop through days of the week
        for iDayOfWeek in range(1, 8) :
            # Read the event list property
            propData = _bacnet.read_property(device, (131, instance, 123, iDayOfWeek))

            # Go through the property list
            iEventIdx = 0
            while iEventIdx < len(propData.value[3].value) :
                # Get type and time 
                iTime = decode_unsigned_integer(propData.value[3].value[iEventIdx].data)
                iType = decode_enumerated(propData.value[3].value[iEventIdx + 1].data)
                
                # Add basic info to the vector
                time_events.append(iDayOfWeek)
                time_events.append(iTime)
                time_events.append(iType)
                
                # What is the context tag?
                if propData.value[3].value[iEventIdx + 2].number == 2:
                    # Context tag 2  - real number
                    dblValue = decode_real(propData.value[3].value[iEventIdx + 2].data)
                    time_events.append(dblValue)
                elif propData.value[3].value[iEventIdx + 2].number == 3:
                    # Context tag 3  - integer
                    iValue = decode_unsigned_integer(propData.value[3].value[iEventIdx + 2].data)
                    time_events.append(iValue)
                elif propData.value[3].value[iEventIdx + 2].number == 4:
                    # Context tag 4  - integer
                    iValue = decode_unsigned_integer(propData.value[3].value[iEventIdx + 2].data)
                    time_events.append(iValue)
                else:
                    # Anything else, we don't care.  Set to zero.
                    iValue =0
                    time_events.append(iValue)
                
                # Increment the index
                iEventIdx += 3
        
        # Save the time events out
        ret['time_events']=time_events


        #----< Build the special events hash table >---------------------
        xcptList = []

        # Read the property
        propData = _bacnet.read_property(device, (131, instance, 38))

        # Go through all the records
        iXcptIdx = 0;
        while iXcptIdx < len(propData.value[2].value) :
            # Declare hash table for this exception record
            xcptInfo = {}

            # Is this a date range (exception) or a
            # ...calendar reference (holiday)?
            if propData.value[2].value[iXcptIdx].number == 1:
                # Date range
                dateRange = []
                
                # Get and encode start date
                dtDate = decode_date(propData.value[2].value[iXcptIdx].value[0].data)
                dateRange.append(dtDate.month)
                dateRange.append(dtDate.day)
                dateRange.append(dtDate.year)
                
                # Get and encode end date
                dtDate = decode_date(propData.value[2].value[iXcptIdx].value[1].data)
                dateRange.append(dtDate.month)
                dateRange.append(dtDate.day)
                dateRange.append(dtDate.year)
                xcptInfo['date_range'] = dateRange
            elif propData.value[2].value[iXcptIdx].number == 3:
                # Calendar reference
                calRef = []
                objId = decode_bacnet_object_identifier(propData.value[2].value[iXcptIdx].data)
                calRef.append(objId.id)
                calRef.append(objId.instance_number)
                xcptInfo['calendar_reference'] = calRef

            # Get priority
            xcptInfo['priority'] = decode_enumerated(propData.value[2].value[iXcptIdx + 2].data)

            # Loop through the events
            xcptEvents = []
            iEventIdx = 0
            while iEventIdx < len(propData.value[2].value[iXcptIdx + 1].value) :
                # Get type and time 
                iTime = decode_unsigned_integer(propData.value[2].value[iXcptIdx + 1].value[iEventIdx].data)
                iType = decode_enumerated(propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 1].data)
                
                # Add time, type to record
                xcptEvents.append(iTime)
                xcptEvents.append(iType)

                # Do we have a value?
                if len(propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].data) > 0:
                    # Yes, what is the context tag?
                    if propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].number == 2:
                        # Context tag 2  - real number
                        dblValue = decode_real(propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].data)
                        xcptEvents.append(dblValue)
                    elif propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].number == 3:
                        # Context tag 3  - integer
                        iValue = decode_unsigned_integer(propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].data)
                        xcptEvents.append(iValue)
                    elif propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].number == 4:
                        # Context tag 4  - integer
                        iValue = decode_unsigned_integer(propData.value[2].value[iXcptIdx + 1].value[iEventIdx + 2].data)
                        xcptEvents.append(iValue)
                    else:
                        # Anything else, we don't care.  Set to zero.
                        iValue =0
                        xcptEvents.append(iValue)
                else:
                    # Add a zero (there are always three parts to our exception "record"
                    xcptEvents.append(0)
                
                # Increment the indices
                iEventIdx += 3
             
            # Store the event list and then put the exception schedule into
            # ...the hash table
            xcptInfo['event_list'] = xcptEvents
            xcptList.append(xcptInfo)

            # Get next event
            iXcptIdx += 3

        # Add special events to the return value
        ret['special_events']=xcptList
        if DEBUG:
            print "--[ Load Data ]-----------------------------------"
            print ret

        # Return the result to the caller
        return ret

    ##
    #  read a calendar object and return it to the caller
    #  @return a dictionary of lists
    #  @param  device
    #  @param  instance
    def readCalendar(self, device, instance):
        ret = {}
        date_list = []
         
        #---< Read the date list >-------------------------------------------
        # Read the date list property
        propData = _bacnet.read_property(device, (6, instance, 23))
         
        # How many time events do we have here?
        iNumDates = len(propData.value[2].value)
         
        # Go through the date list
        for i in range(0, iNumDates):
            # Decode the date
            dtDate = decode_date(propData.value[2].value[i].data)
            #
            # Stuff date values into array
            date_list.append(dtDate.month)
            date_list.append(dtDate.day)
            date_list.append(dtDate.year)
         
        # Add the date list to the hash table
        ret['date_list'] = date_list
         
        # Return the result
        return ret

    ##
    #  Save a schedule out
    #  @return 
    #  @param  device   
    #  @param  instance
    #  @param  dictionary
    def write(self, device, instance, data):
        # Print stuff
        if DEBUG:
            print "--[ Saving Data ]-----------------------------------"
            if data.has_key('effective_period') :
                print data['effective_period']
        if data.has_key('special_events') :
            # Create list of special events to write
            if DEBUG:
                print data['special_events']
            propVal = []
            eventArray = data['special_events']
            for event in eventArray :
                newEvent = trane.sequence.SpecialEvent()
                propVal.append(newEvent)
                if event.has_key('date_range') :
                    dr = event['date_range']
                    newEvent.date_valid = sequence.BACnetDateRange(Date(dr[2],dr[0],dr[1]),
                                                                    Date(dr[5],dr[3],dr[4]))
                    newEvent.event_priority = 150
                else :
                    calRef = event['calendar_reference']
                    newEvent.calendar_period = BACnetObjectIdentifier(6,
                                                                      calRef)
                    newEvent.event_priority = 100
                newEvent.event_list = []
                if event.has_key('event_list') :
                    self._create_event_list(event['event_list'],
                                            newEvent.event_list)
            try :
                tag_value = trane.sequence.context_encode_special_event_list(None,propVal)
                _bacnet.write_property_g3(device, (131, instance, 38),
                                          tag_value.value)
            except (BACnetError, BACnetReject, BACnetAbort) :
                if DEBUG:
                    print "BACnet Error on exception schedule save"
                msglog.exception()
                raise # Re-raise the exception.
            except BACnetTimeout :
                if DEBUG:
                    print "BACnet timeout"
                msglog.exception()
                raise # Re-raise the exception.
            except Exception :
                if DEBUG:
                    print "Error"
                msglog.exception()
                raise # Re-raise the exception.

        if data.has_key('time_events') :
            if DEBUG:
                print data['time_events']
            # Separate the events for each day
            dayList = [[],[],[],[],[],[],[]]
            idx = 0
            el = data['time_events']
            while idx < len(el) :
                # BACnet days are 1-based starting on Sunday.
                # Summit is 0-based starting on Sunday.
                day = el[idx]-1
                dayList[day].append(el[idx+1])
                dayList[day].append(el[idx+2])
                dayList[day].append(el[idx+3])
                idx = idx+4

            # Now write each day's events back to the BCU                
            for x in range(0,7) :
                propVal = []
                self._create_event_list(dayList[x], propVal)
                tag_value = trane.sequence.context_encode_summit_time_event_value_list(None, propVal)
                _bacnet.write_property_g3(device, (131, instance, 123, x+1), tag_value.value)

        # Return result
        return "ok"

    def _create_event_list(self, listFrom, listTo) :
        idx = 0
        while idx < len(listFrom) :
            newEvent = trane.sequence.SummitTimeEventValue()
            newEvent.time = data.Time((listFrom[idx]>>24)&0x000000FF, (listFrom[idx]&0x00FF0000)>>16, (listFrom[idx]&0x0000FF00)>>8)
            newEvent.event_type = listFrom[1+idx]
            # Analog event gets analog value parameter
            if newEvent.event_type == 8 :
                newEvent.analog_value = listFrom[2+idx]
            # Optimal start/stop gets limit time
            elif newEvent.event_type == 3 or newEvent.event_type == 4 :
                newEvent.limit_time = listFrom[2+idx]
            # Night economize gets duration
            elif newEvent.event_type == 7 :
                newEvent.duration = listFrom[2+idx]
            listTo.append(newEvent)
            idx = idx + 3

class Trends(CompositeNode):
    _node_def_id = '43208430-3581-47b1-b128-df0f94d27747'
    def read_trane_trend_list(self, device):
        return read_trane_trend_list(device)
    def read_trane_trend_log(self, device, instance):
        tt = TraneTrend(device, instance)
        return tt.get_utc_subplots()

    
# parses an tsws htm file and collects all the nodes in the tags
class TSWSv2(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.nodes = []
    ##
    # NOTE WE need to handle ARRAYINDEX
    def handle_starttag(self,tag,attr):
        objecttype =None
        instance = None
        propertyid= None
        node_found = 0
        arrayindex = -1
        for a in attr: 
            if a[0] == 'node' or a[0] == 'a_node':
                node_found =1
                if not a[1] in self.nodes:
                    self.nodes.append(a[1])         
            if a[0].lower() == 'objecttype':
                objecttype = a[1]
            if a[0].lower() == 'instance':
                instance = a[1]   
            if a[0].lower() == 'propertyid':
                propertyid = a[1]
                if propertyid == '-1':
                    propertyid = '85'
            if a[0].lower() == 'device':
                device = a[1]
                if device == '-1':
                    device = '1'
            if a[0].lower() == 'arrayindex':
                try:
                    arrayindex = int(a[1])
                except:
                    arrayindex = -1
        if not node_found:
            if objecttype !=None or instance!=None or propertyid!=None:
                if arrayindex > -1:
                    node='/services/network/BACnet/internetwork/Devices/%s/%s/%s/%s/array/%s'  % (device,objecttype,instance,propertyid,int(arrayindex)+1)
                else:
                    node='/services/network/BACnet/internetwork/Devices/%s/%s/%s/%s'  % (device,objecttype,instance,propertyid)
                
                if not node in self.nodes:
                    self.nodes.append(node)
                 
                    
                    
                    
      
