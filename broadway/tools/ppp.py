"""
Copyright (C) 2001 2006 2010 2011 Cisco Systems

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

import sys

def config(user,password,phone_number,idle):
        default_file = open('/etc/ppp/defaultoptions','r')
        options_v = default_file.readlines()
        options_v.append('user '+user+'\012')
        options_v.append('connect \"/usr/sbin/chat -v \'\' AT OK ATDT'+phone_number+' CONNECT \'/d/c\'\"\012')
        options_v.append('idle '+idle+'\012')
        options_file = open('/etc/ppp/options','w')
        options_file.writelines(options_v)
        options_file.close()
        default_file.close()
        secrets_file = open('/etc/ppp/pap-secrets','w')
        secrets_value=[user+'\t','*\t',password+'\t','*\t']
        secrets_file.writelines(secrets_value)
        secrets_file.close()
