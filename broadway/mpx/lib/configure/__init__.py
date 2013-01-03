"""
Copyright (C) 2001 2003 2005 2010 2011 Cisco Systems

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
from _attributes import EConfigurationIncomplete
from _attributes import REQUIRED
from _attributes import as_boolean
from _attributes import as_float_formatted
from _attributes import as_formatted
from _attributes import as_int_formatted
from _attributes import as_long_formatted
from _attributes import as_onoff
from _attributes import as_specified
from _attributes import as_truefalse
from _attributes import as_yesno
from _attributes import flatten_attributes
from _attributes import get_attribute
from _attributes import get_attributes
from _attributes import map_from_attribute
from _attributes import map_from_seconds
from _attributes import map_to_attribute
from _attributes import map_to_seconds
from _attributes import outstanding_attributes
from _attributes import set_attribute
from _attributes import set_attributes
from _attributes import stripped_str

from _configuration import Configuration

from _tree import Iterator

from _xml_handler import parse_xml
from _xml_handler import build_xml
from _xml_handler import interrogate_nodes
from _xml_handler import save_xml
