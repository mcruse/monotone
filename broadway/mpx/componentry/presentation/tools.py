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
import os.path

class PackageFileReader(object):
    """
        Helper object that may be imported and 
        instantiated by any package wishing to 
        export a 'read' function that will read 
        file contents relative to that package's 
        path.  To do so, the module must set a module-level 
        attribute named 'read' referencing this instance.
        For example:
        
        from mpx.componentry.presentation.tools import PackageFileReader
        read = PackageFileReader(__file__)
    """
    
    def __init__(self,package):
        self.package = package
    def read(self,filename):
        filename = os.path.join(os.path.dirname(self.package),filename)
        file = open(filename)
        contents = file.read()
        file.close()
        return contents
    def __call__(self,filename):
        return self.read(filename)

