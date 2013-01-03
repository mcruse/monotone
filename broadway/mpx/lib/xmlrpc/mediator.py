"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import os

from moab.linux.lib.zoneinfo import set_time, get_time
from mpx.lib.node import as_node
from mpx.lib import msglog
from mpx.lib.configure import build_xml,interrogate_nodes
from mpx.lib.exceptions import MpxException


## Class to handle the low-level system calls on the Mediator
#  
class MediatorSystem:
  
  def __init__(self):
    pass
  
  
  ## set_datetime will set the Mediator system date/time
  #
  def set_datetime(self, mmddyyyy, hhmmss, zone=None):
    set_time(mmddyyyy,hhmmss, zone)
  
  
  def get_datetime(self):
    return get_time()
  
  
  ## Return the current 'live' xml configuration from given node
  def get_xml(self, url=None):
    try:
      node = as_node(url)
      xml = interrogate_nodes(node)
      return xml
    except Exception, e:
      msglog.exception()
      raise MpxException(e, 'Error getting node xml configuration: %s' % str(e))
    
      
    
