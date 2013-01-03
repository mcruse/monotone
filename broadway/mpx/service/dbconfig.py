"""
Copyright (C) 2011 Cisco Systems

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
"""
Saves the database configuration details in db.properties.
"""

import os
from base64 import b64encode, b64decode

class DBConfigurator:
    
    def configure(self, config):
        
        fileName = "/var/mpx/config/sw/META-INF/db.properties"
        
        configFile = open(fileName, 'w')
        configFile.write("db.agg.main.url=jdbc:mysql://")
        configFile.write(config.get('dbserver'))
        configFile.write(":")
        configFile.write(config.get('port'))
        configFile.write("/manager_db?rewriteBatchedStatements=true")
        configFile.write("\ndb.agg.main.driver=com.mysql.jdbc.Driver")
        configFile.write("\ndb.agg.main.jpa=com.cisco.cbsbu.springframework.jpa.MySqlDialectCustom")
        configFile.write("\ndb.agg.main.username=")
        configFile.write(config.get('username'))
        configFile.write("\ndb.agg.main.password=ENC(")
        configFile.write(b64encode(config.get('password')))
        configFile.write(")\ndb.search.fetchsize=100")

        configFile.close()
                
#dbconfig = DBConfigurator()
#dbconfig.configure("MAC1", "3306", "user1", "password")

##
# Instantiates and returns DBConfigurator factory.
# @return Instance of DBConfigurator defined in this module.
def factory():
    return DBConfigurator()
