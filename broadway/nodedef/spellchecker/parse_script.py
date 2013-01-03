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
#!/usr/bin/env python-mpx

import string

def strip_and_split(line, lenprefix):      
    line = string.strip(line)

    # First, strip the prefix and the trailing )
    line = line[lenprefix:-1]
  
    data = string.split(line, ",")

    retdata = []
    for x in data:
        if x[0:1] == "'":
            x = x[1:-1]
        retdata.append(x)
    return retdata

def format_parm_line(prefix, data):
    retstr = prefix

    for x in range(0, len(data)):
        y = data[x]
        if x != 0:
            retstr += ","
        if x == 4 or y == "NULL":
            retstr += "%s" % y
        else:
            retstr += "'%s'" % y
    retstr += ")\n"
    return retstr

scriptfilename = "master.script"
outputfilename = "modified.master.script"

prefix1 = "INSERT INTO NODE_DEF VALUES("
lenprefix1 = len(prefix1)
prefix2 = "INSERT INTO NODE_DEF_CONFIG VALUES("
lenprefix2 = len(prefix2)

fix_type = 1

fs = open(scriptfilename, "r")
fo = open(outputfilename, "w")

while 1:
    line = fs.readline()

    if line == "": break

    # This finds nodes
    if string.find(line, prefix1) == 0:
        data = strip_and_split(line, lenprefix1)

    # This finds configuration elements for nodes
    if string.find(line, prefix2) == 0:
        data = strip_and_split(line, lenprefix2)
        parm_name = data[1]
        parm_position = data[4]
        parm_label = data[5]
        uparm_label = string.upper(parm_label)
        parm_desc = data[6]
        if fix_type == 1:
            if (uparm_label == "ENABLE") or (uparm_label == "ENABLED"):
                if parm_label != 'Enabled':
                    #print 'Instr is  %s.' % line
                    data[5] = "Enabled"
                    line = format_parm_line(prefix2, data)
                    #print 'Retstr is %s.' % line
                if parm_desc != "Clear to disable starting.":
                    print 'Warning: Description is ' \
                          '"%s" for %s parm of node %s.' % (data[6],
                                                            data[1],
                                                            data[0])
        if fix_type == 2:
            if (uparm_label == "DEBUG") or (uparm_label == "DEBUG MODE"):
                if parm_label != 'Debug':
                    #print 'Instr is  %s.' % line
                    data[5] = "Debug"
                    line = format_parm_line(prefix2, data)
                    #print 'Retstr is %s.' % line
                if parm_position != '9999':
                    data[4] = "9999"
                    line = format_parm_line(prefix2, data)
                if parm_desc != "Enable extra diagnostics.":
                    #print 'Warning: Description is ' \
                    #       '"%s" for %s parm of node %s.' % (data[6],
                    #                                         data[1],
                    #                                         data[0])
                    data[6] = "Enable extra diagnostics."
                    line = format_parm_line(prefix2, data)

    fo.write(line)
        
fs.close()
fo.close()


# Notes: My current best guess at the structure of the INSERT INTO NODE_DEF VALUES records:
#        01 - Node ID
#        02 - Node Name
#        03 - Node Description
#        04 - Factory for creating an instance of the node (eg 'mpx.service.alias.factory')
#        05 - ?? (Seems to usually be NULL)
#        06 - ?? (Seems to usually be NULL)
#        07 - ?? (Seems to usually be NULL)
#        08 - ?? (Seems to usually be NULL)
#        09 - ?? (Seems to usually be a blank string)
#        10 - ?? (Seems to usually be NULL)
#        11 - ?? (Seems to usually be NULL)
#        12 - ?? (Seems to usually be NULL or blank string)
#        13 - ?? (Seems to usually be NULL or blank string)
#
#        My current best guess at the structure of INSERT INTO NODE_DEF_CONFIG VALUES records:
#        01 - Node ID
#        02 - Parameter Name
#        03 - Parameter Type (Checkbox, Readonly, TextField, ComboBox, Table, Node)
#        04 - Default Value [;Possible Values] (eg 250 or 900;15;30;60;120;240;600;900;1800)
#        05 - Position (This field is an int without 's)
#        06 - Label
#        07 - Description
#        08 - Type of validator (usually NULL, but could be NumberValidator, or ??)
#        09 - Parameters for validator (usually NULL, eg 'not_null="1"; min="10"; max="500";')
