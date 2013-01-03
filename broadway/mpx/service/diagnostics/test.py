"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from mpx.lib import msglog
from mpx.lib.exceptions import EAbstract

class Test(object):
    def __init__(self, **kw):
        self._test_name = 'TestMethods'
        self._nerrors = 0
        self._nwarnings = 0
        for k,v in kw.items():
            setattr(self, k, v)
        # a list of additional method names that
        # are considered public which the wrapping
        # node can delegate to.
        self.public = []
        return
    def runtest(self):
        raise EAbstract
    def log(self, msg, console=False):
        if console:
            print msg
        msglog.log(
            'broadway',
            msglog.types.INFO,
            'Diagnostics (%s): %s' % (self._test_name, msg)
        )
        return
    def passed(self):
        return bool(not(self._nerrors or self._nwarnings)) 
    def _get_errors(self):
        return self._nerrors
    nerrors = property(_get_errors)
    def _get_warnings(self):
        return self._nwarnings
    nwarnings = property(_get_warnings)