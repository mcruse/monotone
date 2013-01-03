"""
Copyright (C) 2001 2003 2010 2011 Cisco Systems

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
# Test cases to exercise the mpx.lib.security.RFunction class.

from mpx_test import DefaultTestFixture, main

from mpx.lib.security import RFunction
from mpx.lib.security import RExec

class TestCase(DefaultTestFixture):
    def test_basic_rfunc(self):
        for f in (int, 'int'):
            for a in (1, '1', (1,), '(1,)'):
                v = RFunction(f,args=a)()
                # An unexpected result would indicate a bug in RFunction.
                if v != 1:
                    raise 'Simple configure resulted in a bad eval: int(1) != %s' \
                          % v
        return
    def test_context_rfunc(self):
        r = RFunction('random.uniform', args=(3,4), context='import random',
                      rexec=RExec())
        v = r()
        try:
            # An unexpected result would indicate a bug in RFunction.
            failed = (v < 3 or v > 4)
        except:
            failed = 1
        if failed:
            raise 'Context configure resulted in a bad eval: not 3 <= %s <= 4' % \
                  v
        return
    def test_dict_namespace_rfunc(self):
        #     Test that a single dictionary can be used as a common global
        # namespace for several Rfunction instances.
        names_to_test = ('as_node', 'os', 'mpx', '__builtins__')
        shared_globals = {}
        functions = []
        for c in ('from mpx.lib.node import as_node', 'import os',
                  'import mpx.lib'):
            f = RFunction(eval, context=c, rexec=shared_globals)
            functions.append(f)
        # Ensure the names are in shared_globals.
        for n in names_to_test:
            if not shared_globals.has_key(n):
                raise 'Name not added to shared_globals: ', n
        # Ensure that all functions can resolve the names.
        for f in functions:
            for n in names_to_test:
                # Since the function is 'eval' this is eval(n) executed using
                # the common namespace.
                f(n)
        return
    def test_rexec_namespace_rfunc(self):
        #     The same as test_dict_namespace_rfunc, but using the namespace
        # from a common RExec instance.
        names_to_test = ('test_uniform', 'test_os', 'UPPERCASE', '__builtins__')
        shared_rexec = RExec()
        functions = []
        for c in ('from random import uniform as test_uniform',
                  'import os as test_os',
                  'from string import uppercase as UPPERCASE'):
            f = RFunction(eval, context=c, rexec=shared_rexec)
            functions.append(f)
        # Ensure that all functions can resolve the names.
        for f in functions:
            for n in names_to_test:
                # Since the function is 'eval' this is eval(n) executed using
                # the common namespace.
                f(n)
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
