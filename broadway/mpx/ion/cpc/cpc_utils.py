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
import array
def convert_ethereal_dump(strs): #has addr, 3 spaces, data, 2 spaces, text use for when dumping from data segment
    strs = strs.splitlines()
    byte_values = []
    for s in strs:
        b = s.split('  ')
        if len(b) > 1:
            b = b[1] #strip off hex address and ........ stuff
            b = b.split(' ')[1:] #break apart individual values
            for v in b:
                byte_values.append(int(v,16))
    return array.array('B', byte_values).tostring()

def convert_ethereal_export(strs): #has addr, 2 spaces, data, 3 spaces, text, use for export of bytes
    #strs = dump.splitlines()
    byte_values = []
    for s in strs:
        b = s.split('  ')
        if len(b) > 1:
            b = b[1] #strip off hex address and ........ stuff
            b = b.split(' ') #break apart individual values
            for v in b:
                byte_values.append(int(v,16))
    return array.array('B', byte_values).tostring()

def load_ethereal(filename):
    f = open(filename)
    lines = f.readlines()
    f.close()
    packets = []
    packet_lines = []
    while lines:
        line = lines.pop(0)
        if len(line) > 4: #has data
            #print line
            packet_lines.append(line)
        else: #blank line
            if len(packet_lines) > 0:
                packets.append(packet_lines)
                #print 'append %d lines' % len(packet_lines)
            packet_lines = []
    if len(packet_lines) > 0:
        packets.append(packet_lines)
        #print 'append %d lines' % len(packet_lines)
    answer = []
    for p in packets:
        bytes = convert_ethereal_export(p)
        i = bytes.find('CPCR') #the dump includes the whole packet, we want just the data section
        #print i
        answer.append(bytes[i:])
    return answer
        






'''
import cpc_decode as c

e = c.load_ethereal('F8 F9 1 export.txt')

s = c.Screen()
s.parse(e[:8])

for x in e[23:36]:
 s.parse(x)

for d in cpc_decode.dumps:
 s.parse(cpc_decode.convert_ethereal_dump_to_bytes(d))
'''
 