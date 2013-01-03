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
#!/usr/local/bin/python2.2

from mpx.lib.log import Log
import time
import sys
#creating the log
l = Log("tmp")

#comfiguring what we want to log ( the fields)
l.configure(["timestamp","KWh","Temp F"])

counter = 0

#start time
t = int(time.time())
x = 0
ADD = 1
TRIM = 0
TRIM_NAME = ""
TRIM_VALUE =""
TRIM_NOT_SET = 1

if len(sys.argv) > 1:
    ADD =  int(sys.argv[1])

if len(sys.argv) > 2:
    TRIM = int(sys.argv[2])

if len(sys.argv) > 3:
    TRIM_NAME = sys.argv[3]

if len(sys.argv) > 4:
    TRIM_VALUE = sys.argv[4]

if TRIM_VALUE != "":
    try:
        TRIM_VALUE = int(TRIM_VALUE)
        
    except:
        TRIM_NOT_SET = 0

    if TRIM_NOT_SET:
        try:
            TRIM_VALUE = float(TRIM_VALUE)
        except:
            TRIM_NOT_SET = 0

    if TRIM_NOT_SET:
        try:
            TRIM_VALUE = string(TRIM_VALUE)
        except:
            TRIM_NOT_SET = 0

end_time = time.time() 

print "end time: " + str(time.ctime(end_time))

t = time.time()
t = t - 10
alpha = ['a','b','c','d','e','f']
while counter < 6:
    #adding some values
    print time.ctime(t)
    if ADD:
        
        l.add_entry((t,alpha[int(x)],x))
    counter = counter + 1
    t = t +1
    #adding 5 mins to the start time
    x = x + 1
    

#getting a range of dates back from the log
start = time.time()-100
end = time.time()

start = 988048523.82612801

start = 'a'
end = 'c'
values = l.get_range("KWh",start,end)

#print 'VALUES: ' + str(values) 
for value in values:
   print value

#print "triming before time: " + str(time.ctime(end_time))
#print end_time
#TRIM_VALUE = 988050255.746292
#if TRIM:
    
#    l.trim_gt(TRIM_NAME,TRIM_VALUE)

print 'get_configuration: ' + str(l.configuration())
print l.describe_column_names()
#print "describing columns:" + str(l.describe_columns())
#print "get columns: " + str(l.get_columns())


    
