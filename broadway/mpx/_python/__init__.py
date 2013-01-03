"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
# Used by packages that contain packages (or modules) whose name conflicts
# with a standard Python module that the package must internally refer to.
# @note Built-in modules do not behave as one would expect when they included
#       in another module.  Specifically, import commands that pass through
#       an included built-in will fail stating that the built in is not a
#       module.  To work around this, the name space of all Python modules
#       (real and build-in) are duplicated in local modules.  This achieves
#       two goals:  First, built-ins can be used in fully qualified module
#       paths (e.g. from mpx._python.exceptions import *).  Second, since
#       this package is loaded into the root mpx package prior to any mpx.lib
#       magic (updating python modules with wrappers, etc), we have references
#       to all of the unadulterated Python objects.
# @note All of the orignal (but possibly modified) modules are also available
#       via a reference named original_<i>target</i>.  There is no guarantee
#       that this references are loadable as modules.

import _sandbox

python_types = _sandbox.types
import types

python_thread = _sandbox.thread
import thread

python_threading =_sandbox.threading
import threading

python_exceptions = _sandbox.exceptions
import exceptions

python_socket = _sandbox.socket
import socket

python_httplib = _sandbox.httplib
import httplib

python_smtplib = _sandbox.smtplib
import smtplib

python_urllib = _sandbox.urllib
import urllib

python_ftplib = _sandbox.ftplib
import ftplib

python_xmlrpclib = _sandbox.xmlrpclib
import xmlrpclib

del _sandbox
