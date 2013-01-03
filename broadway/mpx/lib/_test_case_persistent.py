"""
Copyright (C) 2001 2002 2004 2010 2011 Cisco Systems

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
# Test cases to excercise the persistent data object.

import os
import random

from mpx_test import DefaultTestFixture, main

from mpx import properties
from mpx.lib.exceptions import ENameInUse
from mpx.lib.persistent import PersistentDataObject

class TestDataObject(PersistentDataObject):
    def __init__(self,name):
        PersistentDataObject.__init__(self,name)
        return

class OtherTestDataObject(PersistentDataObject):
    def __init__(self,name,_path):
        PersistentDataObject.__init__(self,name,path=_path)
        return

class TestCase(DefaultTestFixture):
    def __init__(self, methodName):
        self.name = 'mpx.lib.persisent.%d' % os.getpid()
        DefaultTestFixture.__init__(self,methodName)
        return
    def test_upgrade(self):
        from mpx.upgrade.persistent import persistent_0
        old = persistent_0.PersistentDataObject('upgrade_test')
        old.purpose = 'testing'
        old.save()
        old_filename = old._persistent.filename
        del(old.__dict__['_persistent'])
        del(old)
        new = PersistentDataObject('upgrade_test')
        self.failIf(os.path.exists(old_filename),
                    'Upgrade failed to remove old version')
        new.purpose = None
        new.load()
        self.failUnless(new.purpose == 'testing',
                        'Upgrade failed to get old value')
        new.destroy()
        del(new)
        
    def test_creation(self):
        d = None
        try:
            d = TestDataObject(self.name)	# Instanciate the PDO.
        finally:
            if d: d.destroy()		        # Delete the non-existant file.
        return
    def test_save_nothing(self):
        d = None
        try:
            d = TestDataObject(self.name)	# Instanciate empty the PDO.
            d.save()				# Save the empty PDO.
        finally:
            if d: d.destroy()		        # Delete the PDO file.
        return
    def test_save_change_and_reload(self):
        d = None
        try:
            d = TestDataObject(self.name)
            value = random.uniform(1,100)
            d.test = value		# Set a value to save.
            d.save()			# Save the value in the PDO.
            d.test = -value		# Change the value.
            assert d.test != value	# Silly test that the value changed.
            d.load()			# Reload the PDO.
            assert d.test == value	# Confirm the value was restored.
        finally:
            if d: d.destroy()	        # Delete the PDO file.
        return
    def test_non_default_path(self):
        d = None
        try:
            d =  OtherTestDataObject(self.name, properties.VAR_RUN)
            realfn = d._persistent.filename
            if os.path.exists(realfn):
                raise "File exists when it shouldn't: %s." % realfn
            value = random.uniform(1,100)
            d.test = value		# Set a value to save.
            d.save()			# Save the value in the PDO.
            fn = os.path.basename(realfn)
            fullfn = os.path.join(properties.VAR_RUN, fn)
            if not os.path.exists(fullfn):
                msg  = "PDO doesn't seem to be where it should be: "
                msg += "%s vs. %s" % (realfn, fullfn)
                raise msg
        finally:
            if d: d.destroy()	        # Delete the PDO file.
        return
    ##
    # Ensure that you can only only instanciate a PDO with a given name once.
    def test_name_in_use(self):
        d1 = TestDataObject(self.name)
        try:
            d2 = TestDataObject(self.name)
            self.fail("I created a PDO I should have not been outa too!")
        except ENameInUse:
            pass
        return
    ##
    # Ensure deleting a PDO instance allows it's reinstanciation and that the
    # data persists.
    def test_del_pdo(self):
        for i in range(0,10):
            d = TestDataObject(self.name)
            d.i = None
            if i:
                d.load()
                self.assert_comparison("i","==","d.i+1")
            d.i = i
            d.save()
            del d
        return
    ##
    # The use of the WeakValueDict to track name use in PDOs can be susceptable
    # to circular references.  PDO's force a gc.collect() IFF there is a name
    # in use collision and that in turn breaks the circular reference.  This
    # test excercises that logic.
    # it.
    def test_del_circular(self):
        d = TestDataObject(self.name)
        d.circular = d
        del d
        d = TestDataObject(self.name)
        return

#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
