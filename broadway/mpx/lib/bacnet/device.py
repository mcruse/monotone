"""
Copyright (C) 2008 2011 Cisco Systems

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
from mpx.lib.bacnet._bacnet import read_property_g3
from mpx.lib.bacnet._exceptions import *
from mpx.lib import msglog

debug = 0


def child_instance_comparison(a, b):
    if a.instance_number < b.instance_number:
        return -1
    if a.instance_number > b.instance_number:
        return 1
    return 0

def get_object_list(device_instance_number):
        answer = []
        if debug: print 'ion.device.get_object_list from device'
        prop = (8, device_instance_number, 76)
        try:
            r = read_property_g3(device_instance_number, prop)
            answer = r.property_value #a list of tags
        except:
            if debug: print 'reading entire list did not work, try one element at a time'
            answer = []
            #get length of list
            len = read_property_g3(device_instance_number, prop+(0,))
            len = len.property_value[0].value
            if len > 1:
                for i in range(1, len+1):
                    obj_tag = read_property_g3(device_instance_number, prop+(i,)).property_value[0]
                    answer.append(obj_tag)
            msglog.log('bacnet', msglog.types.INFO, 'ObjectList(76) retrieved by individual elements from: %s' % device_instance_number)
        return answer

def discover_children_boids(device_instance_number):
        try:
            pv = get_object_list(device_instance_number)
            if debug: print str(pv)
            boids = []
            for a_tag in pv:
                boids.append(a_tag.value) #add in the BACnetObjectIdentifiers
        except:
            if debug: print '_discover_children_boids exception'
            msglog.exception()
            boids = []
        if debug: print 'boids found: ', str(boids)
        return boids  #all boids, regardless of type.
