"""
Copyright (C) 2006 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

import os
import time
from mpx import properties
from moab.linux.lib import system

 
class TestCase(DefaultTestFixture):
    def test_BOOTTIME(self):
        bt1 = system.BOOTTIME
        time.sleep(2)
        bt2 = system.BOOTTIME
        assert bt1 == bt2, "Boottime should remain constant (%f != %f)." % (bt1, bt2)
    def test_boottime(self):
        bt1 = system.boottime()
        time.sleep(2)
        bt2 = system.boottime()
        difftime = abs(bt1 - bt2)
        assert difftime < .1, "boottimes should be close to equal (%f != %f)." % (bt1, bt2)
    def test_dir_change_1(self):
        dname = os.path.join(properties.TEMP_DIR, "test_1")
        os.makedirs(dname)
        dobj = system.DirChange(dname)
        res = dobj.has_changed()
        assert res == 0, "Directory should not have changed."
        time.sleep(1)
        fname = os.path.join(dname, "myfile.txt")
        f = open(fname, 'w')
        f.close()
        res = dobj.has_changed()
        assert res == 1, "Directory should have changed."
        f = open(fname, 'w')
        f.write('Hello there')
        f.close()
        time.sleep(1)
        res = dobj.has_changed()
        assert res == 0, "Directory should not have changed."
        os.remove(fname)
        res = dobj.has_changed()
        assert res == 1, "Directory should have changed."
    def test_dir_changed_collection_1(self):
        dlist = []
        elist = []
        dcobj = system.DirChangeCollection()
        for c in range(0, 10):
            dname = os.path.join(properties.TEMP_DIR, "test_2_%d" % c)
            os.makedirs(dname)
            dlist.append(dname)
            dcobj.add_dir(dname)
        for c in range(0, 10):
            dname = os.path.join(properties.TEMP_DIR, "test_3_%d" % c)
            os.makedirs(dname)
            elist.append(dname)
        time.sleep(1)
        dname = dlist[0]
        fname = os.path.join(dname, 'myfile.txt')
        f = open(fname, 'w')
        f.close()
        clist = dcobj.get_changed_list()
        assert clist == [dname], "Changed list is not correct (%s vs %s)" % (clist, [dname])
        dname1 = dlist[4]
        dname2 = dlist[7]
        dname3 = dlist[8]
        dname4 = elist[3]
        fname1 = os.path.join(dname1, 'file_1.txt')
        fname2 = os.path.join(dname2, 'file_2.txt')
        f = open(fname1, 'w')
        f.close()
        f = open(fname2, 'w')
        f.close()
        exp_list = [dname1, dname2]
        clist = dcobj.get_changed_list()
        assert clist == exp_list, "Changed list is not correct (%s vs %s)" % (clist, exp_list)
        time.sleep(1)
        os.remove(fname1)
        exp_list = [dname1]
        clist = dcobj.get_changed_list()
        assert clist == exp_list, "Changed list is not correct (%s vs %s)" % (clist, exp_list)
        # Attempt to add a dupe.  We should still only get one change for that directory.
        dcobj.add_dir(dname2)
        os.remove(fname2)
        exp_list = [dname2]
        clist = dcobj.get_changed_list()
        assert clist == exp_list, "Changed list is not correct (%s vs %s)" % (clist, exp_list)
        # Add a dupe using another method, we should still only see one return.
        dobj = system.DirChange(dname3)
        dcobj.add_dir_obj(dobj)
        time.sleep(1)
        fname3 = os.path.join(dname3, 'file_3.txt')
        f = open(fname3, 'w')
        f.close()
        exp_list = [dname3]
        clist = dcobj.get_changed_list()
        assert clist == exp_list, "Changed list is not correct (%s vs %s)" % (clist, exp_list)
        # Check the add_dir_obj functionality
        dobj = system.DirChange(dname4)
        dcobj.add_dir_obj(dobj)
        time.sleep(1)
        fname4 = os.path.join(dname4, 'file_4.txt')
        f = open(fname4, 'w')
        f.close()
        exp_list = [dname4]
        clist = dcobj.get_changed_list()
        assert clist == exp_list, "Changed list is not correct (%s vs %s)" % (clist, exp_list)
        ret = dcobj.dir_is_present(dname3)
        assert ret == 1, "%s does not show as being present" % dname3
        bog_name = 'bogus_dir_should_not_be_present'
        ret = dcobj.dir_is_present(bog_name)
        assert ret == 0, "%s should not be present" % bog_name
        dobj2 = dcobj.get_dir_obj(dname4)
        assert dobj == dobj2, "Incorrect DirChange object returned."
    def test_dir_changed_collection_2(self):
        dlist = []
        elist = []
        dcobj = system.DirChangeCollection()
        for c in range(0, 10):
            dname = os.path.join(properties.TEMP_DIR, "test_3_%d" % c)
            os.makedirs(dname)
            dlist.append(dname)
            dcobj.add_dir(dname)
        time.sleep(1)
        dname1 = dlist[0]
        fname1 = os.path.join(dname1, 'file_1.txt')
        f = open(fname1, 'w')
        f.close()
        # Test with a minimum change of 10 seconds.
        # Note: Because of the test setup (sleeping for 1 second),
        #       we really only get a minimum change time of
        #       around 9 seconds.
        clist = None
        min_time = 10
        st_time = time.time()
        while 1:
            clist = dcobj.get_changed_list(min_time)
            if clist:
                break
            time.sleep(.2)
            if time.time() - st_time > min_time + 3:
                break
        en_time = time.time()
        difftime = en_time - st_time
        if difftime < 10 - 1.05:
            raise "Minimum change time of 10 seconds didn't work.  Instead got %f." % difftime
        if not clist:
            raise "Did not ever get the changed list in %f seconds" % difftime
        if clist != [dname1]:
            raise "Got back the wrong clist (%s vs. %s)" % (str(clist), str([dname1]))
        
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
