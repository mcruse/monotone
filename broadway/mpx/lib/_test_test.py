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

def test():
    result = {}
    f = open("test.log")
    counter1 = 0
    counter2 = 0
    counter3 = 0
    counter4 = 0
    counter5 = 0
    counter6 = 0
    
    for line in f.readlines():
        
        if line.split()[0] == "1":
            counter1 = counter1 + 1
            
        if line.split()[0] == "2":
            counter2 = counter2 + 1
                
        if line.split()[0] == "3":
            counter3 = counter3 + 1
                    
        if line.split()[0] == "4":
            counter4 = counter4 + 1
                        
        if line.split()[0] == "5":
            counter5 = counter5 + 1
                            
        if line.split()[0] == "6":
            counter6 = counter6 + 1

    result["counter1"] = counter1
    result["counter2"] = counter2
    result["counter3"] = counter3
    result["counter4"] = counter4
    result["counter5"] = counter5
    result["counter6"] = counter6

    
    f.close()
    return result


