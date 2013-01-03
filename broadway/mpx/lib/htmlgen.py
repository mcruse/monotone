"""
Copyright (C) 2009 2010 2011 Cisco Systems

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
from __future__ import absolute_import
"""
    Helper classes and functions for HTMLgen usage.
    
    TODO: Find better HTML generation tools/libraries.
"""

from HTMLgen import HTMLgen

class ElementWrapper(HTMLgen.AbstractTag):
    def __init__(self, element):
        self.element = element
        HTMLgen.AbstractTag.__init__(self)
    def __str__(self):
        # Empty AbstractTag output starts with "< ", followed by attrs.
        adornments = HTMLgen.AbstractTag.__str__(self).partition('>')[0][2:]
        open,space,tail = str(self.element).partition(" ")
        return " ".join([open, adornments.strip(), tail])
    def __getattr__(self, name):
        return getattr(self.element, name)

def adorn(element, *attritems, **attrkws):
    """
        Attaches additional attributes to HTMLgen elements 
        such that they will be displayed in output HTML.
        
        Function accepts two forms of attribute speicification 
        arguments.  A variable length list is attribute name/value 
        pairs may be provided, and any number of keyword name/value 
        pairs may be specified.  This enables callers to assign 
        attributes whose names may be Python keywords and therefore 
        not usable in a keyword format.
        
        Example:
        
        >>> div = HTMLgen.Div()
        >>> adorn(div, ("for", "label"), ("class", "cool"), submitMe="true")
    """
    if not isinstance(element, HTMLgen.AbstractTag):
        element = ElementWrapper(element)
    attributes = dict(attritems)
    attributes.update(attrkws)
    for name in attributes.keys():
        entry = "%%(%s)s" % name
        if element.attr_template.count(entry) == 0:
            element.attr_template += entry
        value = ' %s="%s"' % (name, attributes[name])
        element.attr_dict[name] = value
    return element

class ArgsDict(dict):
    def fromargs(klass, *args):
        pairs = [(args[i], args[i+1]) for i in range(0, len(args), 2)]
        return klass(pairs)
    fromargs = classmethod(fromargs)

def KeyWordAssist():
    return ArgsDict.fromargs

