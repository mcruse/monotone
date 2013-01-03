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
#!/usr/bin/python2

import pg

class ProductDB:

    def __init__(self,database,dbhost,dbuser):
        self.db = pg.connect(database,host=dbhost,user=dbuser)


    def alloc_mac(self):
        r = self.db.query('select get_mac()');
        return r.getresult()[0][0]

    def alloc_serial(self,partno):
        
        # where:
        #
        # partno        | product
        # --------------+---------
        # 170-0001-001  | 2400
        # 170-0003-001  | TSWS
        # 170-0002-001  | 1200
        # 170-0004-001  | TSWS GB
        # 170-0005-001  | 2500
        # 170-0006-001  | 1500

        r = self.db.query('select get_serial(\'%s\')'%partno);
        return r.getresult()[0][0]

    def get_macs(self,sn):
        r = self.db.query('select mac0,mac1 from device where serial_number = \'%s\''%sn);
        return r.getresult()[0]

#    def create_device(self,sn,partno)
         # insert into device values (get_serial('170-0006-001'),5,now(),get_mac(),get_mac(),now());
