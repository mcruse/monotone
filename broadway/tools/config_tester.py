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
import os
import stat

_ignore = ['adam4017.py','adam7013.py','adam4021.py','analog_in.py','analog_out.py','digital_in.py','digital_out.py','unknown.py', 'counter.py','dallasbus.py','di.py','relay.py','register_cache.py', 'config.py','_service.py', 'log.py', 'service_interface.py', 'test.py', 'node.py', 'rna.py', 'system.py']

def test(path):
    for file in os.listdir(path):
        if stat.S_ISDIR(os.stat(os.path.join(path, file))[0]):
            test(os.path.join(path, file))
        elif file.count('.py~') or file in _ignore:
            continue
        elif file.count('.py'):
            f = open(os.path.join(path, file), 'r')
            content = f.read()
            f.close()
            if content.count('def configure') != content.count('def configuration'):
                print str('configuration missing ' + str(content.count('def configure') -
                                                         content.count('def configuration')) + ' times in ' + os.path.join(path, file))
