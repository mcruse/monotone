"""
Copyright (C) 2002 2003 2005 2007 2010 2011 Cisco Systems

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
from string import join as _join
from mpx import properties as _properties

_MOE_VERSION = _properties.MOE_VERSION
_RELEASE = _properties.RELEASE_VERSION
try:
    if _properties.PRODUCT_VERSION != "":
        _RELEASE = _properties.PRODUCT_VERSION
except Exception:
    pass

_SERIAL_NUMBER = _properties.SERIAL_NUMBER

class _EscapeSequences:
    CLEAR_SCREEN = "\x1b[;H\x1b[2J"
    BOLD = "\x1b[01m"
    UNDERLINE = "\x1b[01;04m"
    BOLDUNDERLINE = "\x1b[01;04m"
    NORMAL = "\x1b[0m"

class _TextAttributes:
    NORMAL    = 0
    BOLD      = 1
    UNDERLINE = 2

def _embelish_string(text, attributes):
    escape = _EscapeSequences.NORMAL
    if attributes == _TextAttributes.BOLD:
        escape = _EscapeSequences.BOLD
    elif attributes == _TextAttributes.UNDERLINE:
        escape = _EscapeSequences.UNDERLINE
    elif attributes == (_TextAttributes.BOLD|_TextAttributes.UNDERLINE):
        escape = _EscapeSequences.BOLDUNDERLINE
    return _join((escape, text, _EscapeSequences.NORMAL), "")

_MOTD = _join(
    (_EscapeSequences.CLEAR_SCREEN,
     _embelish_string("Mediator Operating Environment %s" % _MOE_VERSION,
                      _TextAttributes.BOLD),
     _embelish_string("Mediator Framework (tm) %s" % _RELEASE,
                      _TextAttributes.BOLD),
     "",
     _embelish_string("Serial number %s" % _SERIAL_NUMBER,
                      _TextAttributes.BOLD),
     "",
     ""),
    '\n')

def as_string():
    return _MOTD
