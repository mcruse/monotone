"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
###
# This module defines utilities for translating CSV documents of points 
# into Machine and Point nodes.  The CSV document is expected to have the 
# following characteristics:
#
# - Header line giving labels for columns.  This is thrown away.
# - Any number of rows with the following columns:
#   - Flag indicating whether row should be turned into point or not.
#   - Integer ID of point matching ID on device.
#   - Name of point.
#   - Dictionary indicating values.  Dict is empty for scalar values.
#       If enumerated value, dictionary should indicate so.
# 
# Example first 4 rows of CSV:
#    Include,Property,Property Name,Enumerated Value
#    0,10199,Alarm Event Class,{}
#    1,10493,Alarm Output,{0: 'Off',1: 'On'}
#    1,11955,Auto/Stop Status,{0: 'Stop',1: 'Auto'}
##

from mpx.lib import msglog

class MachineBuilder(object):
    def __init__(self, input):
        """
            Input should be file-stream like object linked to CSV source.
        """
        self.points = []
        input.seek(0)
        input.readline()
        lines = input.readlines()
        for line in lines:
            try: 
                self.points.append(_PointConfig(line.strip()))
            except Exception, error:
                msglog.log('broadway', msglog.types.INFO, 
                           'Failed to make point from: "%s"' % line.strip())
        return
    
    def build(self, name, parent):
        from machine import Machine
        from machine import Point
        machinenode = Machine()
        machinenode.configure({'name':name, 'parent':parent})
        for point in self.points:
            if not point.include:
                continue
            metadata = []
            metadata.append({'name': 'property', 
                             'definition': point.property})
            metadata.append({'name': 'point_type', 
                             'definition': point.point_type})
            metadata.append({'name': 'value', 
                             'definition': point.value})
            pointnode = Point()
            pointnode.configure({'name':point.name, 
                                 'parent':machinenode, 
                                 'metadata': metadata})
        machinenode.start_simulation()
        return machinenode

class _PointConfig(object):
    def __init__(self, line):
        self.line = line
        splitline = line.split(',', 3)
        self.include = int(splitline[0])
        self.property = int(splitline[1])
        self.name = splitline[2]
        self.value = eval(splitline[3])
        self.point_type = 'enumeration'
        if not self.value:
            self.point_type = 'scalar'
            self.value = 0
        return

