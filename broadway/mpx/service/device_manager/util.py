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
# @idea Passing in globals and locals is to complicated to explain, IHMO.
#       Ideally there should be a way to find the appropriate globals
#       and locals based on the stack frame, although use in overriden
#       functions on classes makes that less obvious than is, um, obvious.
context_map = {}

def import_factory(factory_path, global_context=None, local_context=None):
    if global_context is None:
        global_context = globals()
    if local_context is None:
        local_context = locals()
    gid = id(global_context)
    factory_map = context_map.get(gid,None)
    if factory_map is None:
        factory_map = {}
        context_map[gid] = factory_map
    else:
        factory = factory_map.get(factory_path)
        if factory is not None:
            return factory
    factory_elements = factory_path.split('.')
    factory_name = factory_elements.pop()
    module_name = '.'.join(factory_elements)
    if module_name:
        module = __import__(module_name, global_context, local_context)
        for name in factory_elements[1:]:
            module = getattr(module,name)
        factory = getattr(module, factory_name)
    elif local_context.has_key(factory_name):
        factory = local_context[factory_name]
    else:
        factory = global_context[factory_name]
    factory_map[factory_path] = factory
    return factory

