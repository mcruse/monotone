"""
Copyright (C) 2002 2003 2005 2010 2011 Cisco Systems

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
# Namespace magic that ensures that mpx._python only imports real Python
# modules from the original Python library - not broadway modules with the
# same name.
#
# The strategy is to remove all entries from sys.path that are not canonical
# python folders.  The original way of doing this was to remove all entries
# that did not begin with sys.exec_prefix + "/python" + sys.version[:3].  But
# for some python builds, that did not work because sys.exec_prefix was
# "/usr/bin" instead of "/usr".  So the algorithm has been revised to include
# only those directories that contains the text /pythonX.Y or /pythonXY.zip,
# where X and Y represent the major and minor version.

import os
import sys
import string

python_dir_name = '/python' + sys.version[:3]
python_zip_name = '/python%d%d.zip' % (sys.version_info[0],
                                       sys.version_info[1])
saved_path = []
saved_path.extend(sys.path)
try:
    for dir in tuple(sys.path):
        if dir.find(python_dir_name)<0 and dir.find(python_zip_name)<0:
            sys.path.remove(dir)
    import exceptions
    import types
    import thread
    import threading
    import socket
    import httplib
    import smtplib
    import urllib
    import ftplib
    import xmlrpclib
finally:
    while len(sys.path):
        sys.path.pop()
    sys.path.extend(saved_path)


del sys
del saved_path
del python_dir_name
del python_zip_name
