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
from mpx_test import DefaultTestFixture, main

from mpx.lib import url

if __name__ == '__main__':
    main()

class TestCase(DefaultTestFixture):
    def dump_url(self, path):
        print "\npath = %r\n" % path
        u = url.URL()
        u.parse(path)
        print u
        return
    def test_case_scheme_only(self):
        u = url.URL()
        u.parse('mpx:')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 0)
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.local_path() == '')
        self.assert_(not u.final_slash())
        self.assert_(u.path() == '')
        self.assert_(u.url_path() == 'mpx:')
        self.assert_(u.full_url() == 'mpx:')
        return
    def test_case_scheme_and_root(self):
        u = url.URL()
        u.parse('mpx:/')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '/')
        self.assert_(u.url_path() == 'mpx:/')
        self.assert_(u.full_url() == 'mpx:/')
        return
    def test_case_scheme_and_host(self):
        u = url.URL()
        u.parse('mpx://host')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 0)
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '')
        self.assert_(u.path() == '//host')
        self.assert_(u.url_path() == 'mpx://host')
        self.assert_(u.full_url() == 'mpx://host')
        return
    def test_case_scheme_host_and_root(self):
        u = url.URL()
        u.parse('mpx://host/')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '//host/')
        self.assert_(u.url_path() == 'mpx://host/')
        self.assert_(u.full_url() == 'mpx://host/')
        return
    def test_case_scheme_host_and_dir(self):
        u = url.URL()
        u.parse('mpx://host/dir')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '/dir')
        self.assert_(u.path() == '//host/dir')
        self.assert_(u.url_path() == 'mpx://host/dir')
        self.assert_(u.full_url() == 'mpx://host/dir')
        return
    def test_case_scheme_host_dir_and_slash(self):
        u = url.URL()
        u.parse('mpx://host/dir/')
        self.assert_(u.scheme() == 'mpx')
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/dir/')
        self.assert_(u.path() == '//host/dir/')
        self.assert_(u.url_path() == 'mpx://host/dir/')
        self.assert_(u.full_url() == 'mpx://host/dir/')
        return
    def test_case_scheme_and_triple_slash(self):
        u = url.URL()
        u.parse('file:///')
        self.assert_(u.scheme() == 'file')
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '///')
        self.assert_(u.url_path() == 'file:///')
        self.assert_(u.full_url() == 'file:///')
        return
    def test_case_scheme_triple_slash_and_dir(self):
        u = url.URL()
        u.parse('file:///dir')
        self.assert_(u.scheme() == 'file')
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '/dir')
        self.assert_(u.path() == '///dir')
        self.assert_(u.url_path() == 'file:///dir')
        self.assert_(u.full_url() == 'file:///dir')
        return
    def test_case_scheme_up_one_and_file(self):
        u = url.URL()
        u.parse('http:../index.html')
        self.assert_(u.scheme() == 'http')
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 2 and u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '../index.html')
        self.assert_(u.path() == '../index.html')
        self.assert_(u.url_path() == 'http:../index.html')
        self.assert_(u.full_url() == 'http:../index.html')
        return
    def test_case_empty_path(self):
        u = url.URL()
        u.parse('')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 0)
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '')
        self.assert_(u.path() == '')
        self.assert_(u.url_path() == '')
        self.assert_(u.full_url() == '')
        return
    def test_case_single_dot(self):
        u = url.URL()
        u.parse('.')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 1)
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '.')
        self.assert_(u.path() == '.')
        self.assert_(u.url_path() == '.')
        self.assert_(u.full_url() == '.')
        return
    def test_case_root(self):
        u = url.URL()
        u.parse('/')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '/')
        self.assert_(u.url_path() == '/')
        self.assert_(u.full_url() == '/')
        return
    def test_case_root_and_element(self):
        u = url.URL()
        u.parse('/element')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and
                     not u.segments()[0] and
                     u.segments()[1] == 'element')
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '/element')
        self.assert_(u.path() == '/element')
        self.assert_(u.url_path() == '/element')
        self.assert_(u.full_url() == '/element')
        return
    def test_case_root_dir_and_slash(self):
        u = url.URL()
        u.parse('/dir/')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and
                     not u.segments()[0] and
                     u.segments()[1] == 'dir')
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/dir/')
        self.assert_(u.path() == '/dir/')
        self.assert_(u.url_path() == '/dir/')
        self.assert_(u.full_url() == '/dir/')
        return
    def test_case_root_dir_and_element(self):
        u = url.URL()
        u.parse('/dir/element')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 3 and
                     not u.segments()[0] and
                     u.segments()[1] == 'dir' and
                     u.segments()[2] == 'element')
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '/dir/element')
        self.assert_(u.path() == '/dir/element')
        self.assert_(u.url_path() == '/dir/element')
        self.assert_(u.full_url() == '/dir/element')
        return
    def test_case_triple_slash(self):
        u = url.URL()
        u.parse('///')
        self.assert_(not u.scheme())
        self.assert_(u.host() == '')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '///')
        self.assert_(u.url_path() == '///')
        self.assert_(u.full_url() == '///')
        return
    def test_case_host(self):
        u = url.URL()
        u.parse('//host')
        self.assert_(not u.scheme())
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(not u.is_absolute())
        self.assert_(len(u.segments()) == 0)
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '')
        self.assert_(u.path() == '//host')
        self.assert_(u.url_path() == '//host')
        self.assert_(u.full_url() == '//host')
        return
    def test_case_host_slash(self):
        u = url.URL()
        u.parse('//host/')
        self.assert_(not u.scheme())
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 1 and not u.segments()[0])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/')
        self.assert_(u.path() == '//host/')
        self.assert_(u.url_path() == '//host/')
        self.assert_(u.full_url() == '//host/')
        return
    def test_case_host_dir(self):
        u = url.URL()
        u.parse('//host/dir')
        self.assert_(not u.scheme())
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and
                     not u.segments()[0] and
                     u.segments()[1] == 'dir')
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(not u.final_slash())
        self.assert_(u.local_path() == '/dir')
        self.assert_(u.path() == '//host/dir')
        self.assert_(u.url_path() == '//host/dir')
        self.assert_(u.full_url() == '//host/dir')
        return
    def test_case_host_dir_and_slash(self):
        u = url.URL()
        u.parse('//host/dir/')
        self.assert_(not u.scheme())
        self.assert_(u.host() == 'host')
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and
                     not u.segments()[0] and
                     u.segments()[1] == 'dir')
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '/dir/')
        self.assert_(u.path() == '//host/dir/')
        self.assert_(u.url_path() == '//host/dir/')
        self.assert_(u.full_url() == '//host/dir/')
        return
    def test_case_dreaded_double_slash(self):
        u = url.URL()
        u.parse('//')
        self.assert_(not u.scheme())
        self.assert_(not u.host())
        self.assert_(not u.port())
        self.assert_(u.is_absolute())
        self.assert_(len(u.segments()) == 2 and
                     not u.segments()[0] and
                     not u.segments()[1])
        self.assert_(not u.parameters())
        self.assert_(not u.query())
        self.assert_(not u.fragment())
        self.assert_(u.final_slash())
        self.assert_(u.local_path() == '//')
        self.assert_(u.path() == '//')
        self.assert_(u.url_path() == '//')
        self.assert_(u.full_url() == '//')
        return
