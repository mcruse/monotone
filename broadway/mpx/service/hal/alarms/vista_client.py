"""
Copyright (C) 2003 2010 2011 Cisco Systems

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
from mpx.lib.exceptions import EInvalidValue
from mpx.service.hal.client import Client

class VistaClient(Client):
    def start(self):
        self._history_client = self.parent.get_child('History Client')
        Client.start(self)
    def _check_parameters(self,column,start,end):
        if column != '_seq':
            raise EInvalidValue('column',column,'Value of column must be _seq')
        if end is not None:
            raise EInvalidValue('end',end,'Value of end must be None')
        if start >= 0:
            raise EInvalidValue('start',start,
                                'Value of start must be less than 1')
    def get_range(self,column,start,end=None):
        self._check_parameters(column,start,end)
        return self._history_client.newest_n_alarm_entries(-start)
    def get_range_values(self,column,start,end=None):
        self._check_parameters(column,start,end)
        return self._history_client.newest_n_alarm_values(-start)
    def get_column_names(self):
        return self._history_client.alarm_field_names()
