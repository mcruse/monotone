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
#google spreadsheet node
from xml.etree import ElementTree
import gdata.spreadsheet.service
import gdata.service
import atom.service
import gdata.spreadsheet
import atom
import getopt
import sys
import string

import time, types
from mpx.lib import msglog
from mpx.lib import EnumeratedValue
from mpx.lib import thread_pool
from mpx.lib import Callback
from mpx.ion import Result

from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib.node import CompositeNode, as_node_url, as_internal_node, as_node
from mpx.lib.node.auto_discovered_node import AutoDiscoveredNode
from mpx.lib.node.proxy import ProxyAbstractClass
from mpx.lib.threading import ImmortalThread, Lock
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.exceptions import ENoSuchName, EUnknownScheme
from mpx.lib.scheduler import scheduler
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER as SM
from mpx.lib import msglog

class SpreadSheet(CompositeNode):
    def __init__(self):
        self.url = None #http://spreadsheets.google.com/tq%3Fkey%3DpwMil7%2DRME4jnneXtT2vSOQ%26range%3DB9%3AB13%26gid%3D0
        self.user = None
        self.password = None
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'url', '', config, str)
        set_attribute(self, 'user', '', config, str)
        set_attribute(self, 'password', '', config, str)
        set_attribute(self, 'spreadsheet', self.name, config, str) #spreadsheet name
        set_attribute(self, 'worksheet', '', config, str)
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'url', config, str)
        get_attribute(self, 'user', config, str)
        get_attribute(self, 'password', config, str)
        get_attribute(self, 'spreadsheet', config, str)
        get_attribute(self, 'worksheet', config, str)
        return config
    def start(self):
        self.restart()
        CompositeNode.start(self)
    def restart(self):
        self.gd_client = gdata.spreadsheet.service.SpreadsheetsService()
        self.gd_client.email = self.user
        self.gd_client.password = self.password
        self.gd_client.source = 'Spreadsheets GData Sample'
        self.gd_client.ProgrammaticLogin()
        self.curr_key = ''
        self.curr_wksht_id = ''
        self.list_feed = None
        # Get the list of spreadsheets and find the one that matches the node's name
        feed = self.gd_client.GetSpreadsheetsFeed()
        i = self._parse_spreadsheets_feed(feed)
        id_parts = feed.entry[i].id.text.split('/')
        self.curr_key = id_parts[len(id_parts) - 1]
        # Get the list of worksheets
        feed = self.gd_client.GetWorksheetsFeed(self.curr_key)
        i = self._parse_worksheets_feed(feed)
        id_parts = feed.entry[i].id.text.split('/')
        self.curr_wksht_id = id_parts[len(id_parts) - 1]
    def _parse_spreadsheets_feed(self, feed):
        for i, entry in enumerate(feed.entry):
            print '%s %s\n' % (i, entry.title.text)
            if entry.title.text == self.spreadsheet: #match the spreadsheet name
                return i
        return 0
    def _parse_worksheets_feed(self, feed):
        for i, entry in enumerate(feed.entry):
            print '%s %s\n' % (i, entry.title.text)
            if entry.title.text == self.worksheet: #match the worksheet name
                return i
        return 0
    def _parse_cells_feed(self, feed):
        cells_dict = {}
        for i, entry in enumerate(feed.entry):
            print '%s %s\n' % (entry.title.text, entry.content.text)
            cells_dict[entry.title.text]=entry.content.text
        return cells_dict
    def get_range(self, top_left, bottom_right=None):
        #top_left and bottom_right can be strings 'R1C1' or 'A1' or tuples/lists (R#, C#)
        if type(top_left) in (tuple, list):
            top_left = 'R%dC%d' % top_left
        range = top_left
        if bottom_right:
            if type(bottom_right) in (tuple, list):
                bottom_right = 'R%dC%d' % top_left
            range += ':' + bottom_right
        query = gdata.spreadsheet.service.CellQuery()
        query['range'] = range
        feed = self.gd_client.GetCellsFeed(self.curr_key, self.curr_wksht_id, query=query)
        return self._parse_cells_feed(feed)
class AutoConfiguredSpreadSheet(SpreadSheet): 
    #reads column A (which contains node urls) and B which contains direction (0=read_only, 1=bi-mpx-leads, 2=bi-doc-leads, 3=write_only), and places values in C
    def __init__(self):
        SpreadSheet.__init__(self)
        self.sheet = {} #[(url, mode, value)], list of tuples
        self.sid = None #subscription for points we read from mpx
        self.max_row = 100
        self.period = 5
        self.running = 1
        self.node_values = {}
    def restart(self):
        print 'restart'
        SpreadSheet.restart(self) #connect
        scheduler.after(self.period, self.resync)
    def resync(self):
        try:
            print 'resync'
            new_sheet = self.get_sheet()
            #subscribe to nodes that need to be read
            sub_dict = {} #dictionary to create subscriptions
            for row_index in new_sheet.keys():
                url, mode, value = new_sheet[row_index]
                if mode < 3: #need to subscribe to non-write-only
                    sub_dict[row_index] = url
                #for nodes that need to be set from values in the spreadsheet
                if mode == 2 or mode == 3: #need to set
                    try:
                        as_node(url).set(value) #value is a string or None
                    except:
                        msglog.exception()
            self.sheet = new_sheet
            if sub_dict: #create a new subscription then delete the old one
                sid = SM.create_polled(sub_dict)
                if self.sid:
                    SM.destroy(self.sid)
                self.sid = sid
                sub_dict = SM.poll_all(sid)
                self.node_values = sub_dict
                #update the spread sheet
                for row_index in sub_dict.keys():
                    url, mode, value = new_sheet[row_index]
                    if mode == 0 or mode == 1: #need to write
                        try:
                            self.set_cell(row_index, 3, sub_dict[row_index]['value']) 
                        except:
                            msglog.exception()
            #the spreadsheet and mediator should now be in sync
            self.scan()
        except:
            msglog.exception()
    def scan(self):
        print 'scan'
        try:
            if self.running:
                self.scan_nodes_for_changes()
                self.scan_spread_sheet_for_changes()
                scheduler.after(self.period, self.scan)
        except:
            msglog.exception()
            scheduler.after(self.period, self.restart)
    def scan_nodes_for_changes(self):
        sub_dict = SM.poll_all(self.sid)
        self.node_values=sub_dict
        print 'scan_nodes_for_changes sm:', sub_dict
        if sub_dict: #if there have been any changes
            #look at the value in the sheet and send it if there is a difference
            for row_index in sub_dict.keys():
                try:
                    url, mode, value = self.sheet[row_index]
                    new_value = sub_dict[row_index]['value']
                    if mode < 3: #not write only
                        update = 0
                        print "compare: ", str(new_value), value
                        if str(new_value) != value:
                            update = 1
                            try:
                                if new_value == eval(value): #check numeric comparison
                                    update = 0
                            except:
                                pass #text words won't eval
                        if update:
                            print 'scan_nodes_for_changes set_cell:', row_index
                            self.set_cell(row_index, 3, new_value) 
                except:
                    msglog.exception()
    def scan_spread_sheet_for_changes(self):
        new_sheet = self.get_sheet()
        for row_index in new_sheet.keys():
            url, mode, value = new_sheet[row_index]
            o_url, o_mode, o_value = self.sheet.get(row_index, [None,None,None])
            if o_url != url or o_mode != mode or len(new_sheet) != len(self.sheet): #spreadsheet has changed!!!  stop in your tracks and resync in 10 seconds
                raise EUnknownScheme()
            if mode != 0: #not read only
                #for nodes that CAN be set from values in the spreadsheet
                #compare old spread sheet to new
                    if o_value != value: #the sheet value has changed
                        try:
                            print 'scan_spread_sheet_for_changes set:', url, value
                            as_node(url).set(value) #value is a string or None
                        except:
                            msglog.exception()
        self.sheet = new_sheet
    def get_sheet(self):
        cells_dict = self.get_range('R2C1','R%dC3' % self.max_row)
        a_keys = filter(lambda s: s[0]=='A', cells_dict.keys())
        a_keys.sort()
        answer = {} #dict of (node_url, r/w mode, value) keyed by str(row number)
        for k in a_keys:
            url = cells_dict[k]
            row_index = k[1:] #note: this is still a string of a number
            try:
                mode = int(cells_dict.get('B'+row_index,0)) #default mode is read write - mpx lead
            except:
                mode = 0
            value = cells_dict.get('C'+row_index,None)
            answer[row_index] = [url, mode, value,]
        return answer
    def set_cell(self, row, col, inputValue):
        entry = self.gd_client.UpdateCell(row=str(row), col=str(col), inputValue=str(inputValue), 
                key=self.curr_key, wksht_id=self.curr_wksht_id)
        if isinstance(entry, gdata.spreadsheet.SpreadsheetsCell):
            print 'Updated!', row, col, inputValue
            #update local copy of sheet for COV testing
            self.sheet[str(row)][2] = str(inputValue)
class Cell(CompositeNode):
    def __init__(self):
        self.column = None
        self.row = None
    def configure(self, config):
        CompositeNode.configure(self, config)
        set_attribute(self, 'column', 0, config, int) #must be > 0
        set_attribute(self, 'row', 0, config, int) #must be > 0
        set_attribute(self, 'cell', '', config, str) #ie: H42
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'column', config, str)
        get_attribute(self, 'row', config, str)
        get_attribute(self, 'cell', config, str)
        return config
    def get(self, skipcache=0):
        query = gdata.spreadsheet.service.CellQuery()
        if self.cell: #cell type reference overrules row / column
            query['range'] = self.cell
        else:
            query['range'] = 'R%dC%d' % (self.row,self.column)
        feed = self.parent.gd_client.GetCellsFeed(self.parent.curr_key, self.parent.curr_wksht_id, query=query)
        return self._parse_cells_feed(feed)
    def set(self, inputValue):
        entry = self.parent.gd_client.UpdateCell(row=str(self.row), col=str(self.column), inputValue=str(inputValue), 
                key=self.parent.curr_key, wksht_id=self.parent.curr_wksht_id)
        if isinstance(entry, gdata.spreadsheet.SpreadsheetsCell):
            print 'Updated!'
    def _parse_cells_feed(self, feed):
        answer = []
        for i, entry in enumerate(feed.entry):
            print '%s %s\n' % (entry.title.text, entry.content.text)
            answer.append((entry.title.text, entry.content.text,))
            return entry.content.text
        return answer
        
'''
from mpx.lib.node import as_node
p = as_node('/services/network')
config = {'name':'walgreens_via_rna_tunnel',
          'parent':p,
          'user':'rzmediator',
          'password':'mpxadmin',
          'worksheet':'Sheet1'}
a.prune()
a = AutoConfiguredSpreadSheet()
a.configure(config)
a.start()
'''
'''
from mpx.lib.node import as_node
p = as_node('/services/network')
config = {'name':'mpxadmin',
          'parent':p,
          'user':'rzmediator',
          'password':'mpxadmin',
          'worksheet':'Sheet1'}
s = SpreadSheet()
s.configure(config)
s.start()

config = {'name':'cell1',
          'parent':s,
          'column':'2',
          'row':'9'}
c = Cell()
c.configure(config)

c.get()
c.set(555)

http://spreadsheets.google.com/ccc?key=pwMil7-RME4jnneXtT2vSOQ&hl=en
'''
