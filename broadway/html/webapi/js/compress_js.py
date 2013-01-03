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
import string
import sys
in_file = 'sdk.js'
out_file = "new.js"
f = open(in_file,'r')
of = open(out_file,'w')
long_comment = 0
SKIP = 0
if len(sys.argv) >=2:
    LIMIT = int(sys.argv[1])
else:
    LIMIT = 1000000
print 'limit: %s' % LIMIT
line_num = 1
for l in f.xreadlines():
    l = string.strip(l)

    if not long_comment:
        if l[0:2] == '/*':
            long_comment = 1
            #if l[0:6] == '/*SKIP':
            #   SKIP = 1         
            #   of.write('\n' + l + '\n' )
        elif l[0:2] == '//':
            pass
        else:
            if line_num < LIMIT:
                of.write(l )
            else:
                of.write(l + '\n' )
    else:
        #if SKIP:
        #    of.write(l + '\n' )
        if l[-2:] == '*/':
            long_comment = 0
    line_num += 1

    
