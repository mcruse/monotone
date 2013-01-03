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
from mpx.componentry import adapts
from mpx.componentry import implements
from mpx.componentry import provided_by
from mpx.componentry import register_adapter
from mpx.lib.interfaces import IInspectable
Defined = object()
Undefined = object()

class Inspector(object):
    adapts(None)
    implements(IInspectable)
    def __init__(self, subject):
        self.subject = subject
        super(Inspector, self).__init__()
    def _typename(self):
        return self.subject.__class__.__name__
    def attr(self, name, value=Undefined):
        current = self.getattr(name, None)
        if value is not Undefined:
            self.setattr(name, value)
        return current
    def hasattr(self, name):
        try:
            self.getattr(name)
        except AttributeError:
            exists = False
        else:
            exists = True
        return exists
    def getattr(self, name, default=Undefined):
        value = getattr(self.subject, name, default)
        if value is Undefined:
            # Two-argument getattr used and no attribute exists.
            message = "'%s' object has no attribute '%s'"
            raise AttributeError(message % (self._typename(), name))
        return value
    def setattr(self, name, value):
        return setattr(self.subject, name, value)
    def has_method(self, name):
        return callable(self.getattr(name, None))
    def get_method(self, name, default=Undefined):
        if not self.has_method(name) and self.hasattr(name):
            # TypeError if attribute exists but is not callable.
            message = "'%s' object attribute '%s' not callable"
            raise TypeError(message % (self._typename(), name))
        return self.getattr(name, default)
    def provides_interface(self, interface):
        if isinstance(interface, str):
            try:
                eval(interface)
            except NameError:
                module,sep,datatype = interface.rpartition(".")
                if not module:
                    raise
                exect("import " + module)
            interface = eval(interface)
        return interface.providedBy(self.subject)
    def get_interfaces(self, named=False):
        interfaces = list(provided_by(self.subject))
        if named:
            items = []
            for interface in interfaces:
                items.append((interface.__module__, interface.__name__))
                interfaces = [".".join(item) for item in items]
        return interfaces

register_adapter(Inspector)