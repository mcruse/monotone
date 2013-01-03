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
from mpx.lib.configure import REQUIRED
from mpx.lib.configure import get_attribute
from mpx.lib.configure import set_attribute

from _node import CompositeNode

##
# Do nothing conversion function.
#
# @param value.
# @returns <code>value</code>.
def _no_conversion(value):
    return value

##
# A NodeDecorator essentially provides a dynamic mixin capabilitiy.  Adding new
# attributes and (someday) new behaviors to parent Nodes at runtime.
#
# @fixme Ideally, this wouldn't really be a full-blown node.
class NodeDecorator(CompositeNode):
    ##
    # Provides a sanity check to enforce the convention of naming decorations
    # with a common prefix followed by an underbar.
    _PREFIX = None
    ##
    # A convenience:
    REQUIRED = REQUIRED
    ##
    # After __init__() completes, __setattr__() does not allow the dynamic
    # creation of attributes.  This is largeley to catch incorrect use of
    # mpx.lib.configure.set_attribute() which is generally NOT correct to use
    # when implementing NodeDecorator subclasses.  In cases where such use
    # makes sense, declare those attributes in __init__() BEFORE calling
    # NodeDecorator.__init__()
    def __setattr__(self, name, value):
        if self.__locked_down and not hasattr(self, name):
            # @fixme HACK if condition is related to too much magic.  Fixme
            #        when the nodes are refecatored:
            if name not in ('__factory__', '__node_id__'):
                raise AttributeError("NodeDecorator's do not support dynamic"
                                     " creation of attributes.")
        CompositeNode.__setattr__(self, name, value)
        return
    def __init__(self):
        CompositeNode.__setattr__(self, '_NodeDecorator__locked_down', False)
        CompositeNode.__init__(self)
        # HACK:  Create default attributes before "locking down" this node's
        #        attributes.
        CompositeNode.configure(self, {})
        self.__locked_down = True
        assert self._PREFIX is not None, (
            "Concrete class must set _PREFIX class variable."
            )
        assert self._PREFIX[-1] == '_', (
            "_PREFIX class variable must end in an underbar (_)."
            )
        return
    def set_attribute(self, name, default, dictionary,
                      conversion=_no_conversion):
        assert name.startswith(self._PREFIX), (
            "%s attribute names must start with the %r prefix." %
            (self.__class__.__name__, self._PREFIX)
            )
        return set_attribute(self.parent, name, default, dictionary,
                             conversion)
    def get_attribute(self, name, dictionary,
                      conversion=_no_conversion, *vargs):
        assert name.startswith(self._PREFIX), (
            "%s attribute names must start with the %r prefix." %
            (self.__class__.__name__, self._PREFIX)
            )
        return get_attribute(self.parent, name, dictionary, conversion, *vargs)
