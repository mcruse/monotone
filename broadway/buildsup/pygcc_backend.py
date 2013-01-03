"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
#!/usr/bin/env python-mpx
#-*-Python-*- Hint to [X]Emacs on colorization, etc...
#
# NOTE: This program is generated automagically by configure.  Any changes
#       you make to this POS script will be lost.

import py_compile
import sys
import StringIO

def main( ):

    sourcefile = ""
    targetfile = ""

    argc = len( sys.argv[1:] )

    sourcefile = sys.argv[1]

    if argc == 2:
        targetfile = sys.argv[2]

    s = StringIO.StringIO()
    save_stderr = sys.stderr
    sys.stderr = s
    ok = 0
    try:
        py_compile.compile( sourcefile, targetfile )
        ok = 1
    finally:
        sys.stderr = save_stderr
        s.seek(0)
        result = s.read()
        if result:
            sys.stderr.write(result)
            ok = 0
    return ok

if __name__ == '__main__':
    exit_status = not main( )
    sys.exit( exit_status )
