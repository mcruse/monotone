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
import string

class Dictionary(dict):
    """
        Dictionary extension for use in place of dictionaries requiring
        python 2.3+ dict features 'fromkeys', 'pop', and/or 'copy'.
    """
    def fromkeys(keys):
        return Dictionary([(key,None) for key in keys])
    fromkeys = staticmethod(fromkeys)

    def pop(self, key, default = 'UnsetByCaller'):
        value = self.get(key, default)
        if value == 'UnsetByCaller':
            raise KeyError(key)
        if value is not default:
            del(self[key])
        return value
    def copy(self):
        copy = super(Dictionary, self).copy()
        return type(self)(copy)

class String(str):
    """
        String extension to provide 3-argument slice syntax;
        3rd argument is step value.

        NOTE: not currently in use; it appears the inability to
        pass 3 args to __getslice__ using [:] syntax is more
        fundamental than we are able to wrap without more
        consideration.
    """
    def __getslice__(self, i, j, k=1):
        print '__getslice__(%s, %s, %s)' % (i, j, k)
        substring = self.data[i:j]
        if k == 1: return substring
        start = 0
        end = len(substring)
        if k < 0:
            start, end = end - 1, start - 1
        indices = range(start, end, k)
        splitstring = list(substring)
        return string.join([splitstring[i] for i in indices], '')

