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
from mpx.lib.exceptions import ENameInUse, ENoSuchName
from mpx.lib import msglog


class _ListData: # for exclusive use by MultiListMixin class
    def __init__(self, ml, is_head=0):
        self._multilist = ml
        self._prev = None
        self._next = None
        self._head = None # allows quick get on length and tail
        if is_head:
            self._prev = self
            self._next = self
            self._head = self
            self._len = 0 # - subclass instances do NOT have this attribute;
                          #   do not count head as elem
        return

class MultiListMixin: # normally a base class; standalone as list head
    ##
    # @note subclass must call this method in subclass's own __init__()
    def __init__(self, list_id=None):
        if list_id == 0:
            msglog.log('mpx:rz',msglog.types.ERR,'List ID is "0":')
            msglog.traceback()
        self._list_conns = {} # K: list_id, V: ListData instance
        if not list_id is None: # creating a standalone list head object
            self._list_conns[list_id] = _ListData(self,1)
        return
    def is_in_list(self, list_id):
        return self._list_conns.has_key(list_id)
    def ml_length(self, list_id):
        return self._list_conns[list_id]._head._len
    def ml_get_next(self, list_id):
        return self._list_conns[list_id]._next._multilist
    def ml_get_prev(self, list_id):
        return self._list_conns[list_id]._prev._multilist
    def ml_remove(self, list_id):
        if not self._list_conns.has_key(list_id):
            return
        list_data = self._list_conns[list_id]
        list_head = list_data._head
        list_head._len -= 1
        if list_head._len < 0:
            list_head._len = 0
        list_data._prev._next = list_data._next
        list_data._next._prev = list_data._prev
        list_data._prev = None
        list_data._next = None
        list_data._head = None
        del self._list_conns[list_id]
        return
    def ml_insert_elem_as_next(self, next_ml, list_id):
        next_ml.ml_remove(list_id)
        next_ld = _ListData(next_ml)
        next_ml._list_conns[list_id] = next_ld
        list_data = self._list_conns[list_id]
        next2_ld = list_data._next
        list_data._next = next_ld
        list_data._next._prev = list_data
        list_data._next._next = next2_ld
        list_data._next._head = list_data._head
        next2_ld._prev = next_ld
        list_data._head._len += 1
        return
    def ml_insert_elem_as_prev(self, prev_ml, list_id):
        prev_ml.ml_remove(list_id) #does this make sure this item is not already in list?
        prev_ld = _ListData(prev_ml) #wrap data in a list element
        prev_ml._list_conns[list_id] = prev_ld
        list_data = self._list_conns[list_id] #get head of list
        prev2_ld = list_data._prev
        list_data._prev = prev_ld
        list_data._prev._prev = prev2_ld
        list_data._prev._next = list_data
        list_data._prev._head = list_data._head
        prev2_ld._next = prev_ld
        list_data._head._len += 1
        return
    def ml_clear(self, list_id):
        head = self._list_conns[list_id]._head
        while not head._next is head:
            head._next._multilist.ml_remove(list_id)
        return head
