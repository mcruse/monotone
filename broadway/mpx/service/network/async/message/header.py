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

class Header(object):
    def __init__(self, name = '', value = ''):
        self.set_name(name)
        self.set_value(value)
    def set_name(self, name):
        self.name = name.capitalize()
    def set_value(self, value):
        self.value = value.strip()
    def to_tuple(self):
        return (self.name, self.value)
    def to_dict(self):
        return {self.name: self.value}
    def to_string(self):
        return '%s: %s' % self.to_tuple()
    def from_tuple(klass, headertuple):
        return klass(*headertuple)
    from_tuple = classmethod(from_tuple)
    def from_dict(klass, headerdict):
        return klass.from_tuple(headerdict.items()[0])
    from_dict = classmethod(from_dict)
    def from_string(klass, header):
        name, value = header.strip().split(':', 1)
        return klass(name, value)
    from_string = classmethod(from_string)

class HeaderDictionary(dict):
    def add_header(self, header):
        self[header.name] = header
    def get_header(self, name, default = None):
        return self.get(name.capitalize(), default)
    def get_header_value(self, name, default = None):
        header = self.get_header(name)
        if header:
            return header.value
        return default
    def get_headers(self):
        return self.values()
    def get_header_values(self):
        return [header.name for header in self.get_headers()]
    def get_header_names(self):
        return self.keys()
    def has_header(self, header):
        return self.has_header_named(header.name)
    def has_header_named(self, name):
        return self.has_key(name.capitalize())
    def remove_header(self, header):
        self.remove_header_named(header.name)
    def remove_header_named(self, name):
        del(self[name.capitalize()])
    def to_name_header_tuples(self):
        return self.items()
    def to_name_value_tuples(self):
        return [header.to_tuple() for header in self.get_headers()]
    def to_name_header_dict(self):
        return dict(self)
    def to_name_value_dict(self):
        return dict(self.to_name_value_tuples())
    def to_strings(self):
        return [header.to_string() for header in self.get_headers()]
    def to_string(self):
        strings = self.to_strings()
        return string.join(strings, '\r\n')
    def to_message_header(self):
        headerstring = self.to_string()
        return string.join([headerstring] + ['\r\n'], '\r\n')
    def from_headers(klass, headers):
        headertuples = [(header.name, header) for header in headers]
        return klass.from_name_header_tuples(headertuples)
    from_headers = classmethod(from_headers)
    def from_name_header_tuples(klass, headertuples):
        return klass(headertuples)
    from_name_header_tuples = classmethod(from_name_header_tuples)    
    def from_name_value_tuples(klass, headertuples):
        headers = map(Header.from_tuple, headertuples)
        return klass.from_headers(headers)
    from_name_value_tuples = classmethod(from_name_value_tuples)
    def from_name_header_dict(klass, headersdict):
        return klass(headersdict)
    from_name_header_dict = classmethod(from_name_header_dict)
    def from_name_value_dict(klass, headersdict):
        return klass.from_name_value_tuples(headersdict.items())
    from_name_value_dict = classmethod(from_name_value_dict)
    def from_strings(klass, headerstrings):
        headerstrings = join_continued_headers(headerstrings)
        return klass.from_headers(map(Header.from_string, headerstrings))
    from_strings = classmethod(from_strings)
    def from_string(klass, headerstring):
        return klass.from_headers(map(Header.from_string, headerstring))
    from_string = classmethod(from_string)
    def from_header_message(klass, headerstring):
        return klass.from_string(headerstring.strip())
    from_header_message = classmethod(from_header_message)

def join_continued_headers(headerlines):
    headers = []
    for i in range(len(headerlines)):
        if headerlines[i][0] in ' \t':    
            headers[-1] = headers[-1] + headerlines[i][1:]
        else:
            headers.append(headerlines[i])
    return headers

