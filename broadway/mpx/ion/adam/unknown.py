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
##
# @todo Needs to scan for any modules that would satisfy
# the version.

from mpx.lib import msglog

from module import Module

class Unknown(Module):
    def __init__(self):
        Module.__init__(self)

    def configure(self, config):
        Module.configure(self, config)
        if not self.version:
            self.version = m.ReadModuleName()
        # Import appropriate the ADAM module (or package).
        module = 'mpx.ion.adam.adam' + self.version
        command = compile('import ' + module,
                          'mpx.ion.adam.unknown.configure()', 'exec')
        eval(command)
        # Get the module's factory and instanciate the "real" class.
        command = module + '.factory'
        adam_factory = eval(command, globals(), locals())
        self.instance = adam_factory()
        
        # Scary stuff.  Detach this ion from our parent, configure the real
        # instance (thus attaching it to the parent) and then morph this
        # instance to behave like the real instance (in case anyone has a
        # handle to this instance).
        try:
            self.parent._del_child(self.name)
            self.instance.configure(config)
            attributes = vars(self.instance.__class__)
            attributes.update(vars(self.instance))
            for attrribute in attributes:
                setattr(self, attrribute, getattr(self.instance, attrribute))
        except:
            msglog.exception()
            # The scary stuff failed, reattach to the parent.
            try:
                self.parent._del_child(self.instance.name)
            except:
                pass
            self.parent._add_child(self)
