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
from mpx.componentry.future import newstring as string
from os import path
from mpx.componentry import implements, adapts
from interfaces import ITemplate

class TemplateProcessor(string.Template):
    implements(ITemplate)

    def __init__(self,format_data,force_as_file=False):
        if force_as_file or path.exists(format_data):
            file = open(format_data, 'r')
            format_data = file.read()
            file.close()
        super(TemplateProcessor, self).__init__(format_data)

    def _verify_mapping(self, mapping):
        """
            Reason for converting the mapping
            from a list to a map, if it originally
            is a list that is passed in, is so that
            templates can be used for positioning/formatting
            as well as value-substitution.  For example:
                - given mapping ['name','time','value'], and
                - template: "$time $name",
            substitue would set positioning as well as filter out
            "value" for template's output.
        """
        if type(mapping) is dict:
            return mapping
        elif type(mapping) is list:
            keys = map(str,mapping)
            mapping = dict(zip(keys,mapping))
            return mapping
        else:
            raise TypeError("dict or list requried")
    def substitute(self, mapping, **kw):
        mapping = self._verify_mapping(mapping)
        return super(TemplateProcessor, self).substitute(mapping,**kw)
    def safe_substitute(self, mapping, **kw):
        mapping = self._verify_mapping(mapping)
        return super(TemplateProcessor, self).safe_substitute(mapping,**kw)

