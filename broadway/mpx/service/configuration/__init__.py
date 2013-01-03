"""
Copyright (C) 2001 2010 2011 Cisco Systems

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
##
# Defines the interfaces required to configure and commumicate with the
# configuration service.

from _const import SOFT_EXIT, HARD_EXIT
from _mediator import Service

##
# Instantiates an unconfigured mpx.service.configuration.Service object.
# The object instantiated is known as a <i>mediator</i> in the Broadway
# architecture.  It is the object that provides the configuration of the
# configuration service, and coordinates the collection of objects used to
# implement the service.  A different class of object is returned when the
# configuration service is looked up by name.  When a reference is returned
# to the existing configuration service, it is a reference to it's
# <i>facade</i>.  The <i>facade</i> is the service's public interface, which
# provides all of the publicly available methods for the service.
# @returns An unconfigured instance of mpx.service.configuration.Service.
def factory():
    return Service()
