"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
import compileall
from tools.lib import os
from stat import *

errors_are_fatal = {}
verbosity = {}
debug = {}

##
# @fixme Pass force to sub-scripts...
def compile_dir_and_recurse(dir,level,force):
    global debug
    global verbosity
    global errors_are_fatal
    pid = os.getpid()
    os.chdir(dir)
    if force:
        if verbosity[pid] > 1:
            v = 'v'
        else:
            v = ''
        os.system("rm -%sf *.so *.o *.pyc" % v)
    flist = os.listdir('.')
    if 'compile' in flist:
        os.system(os.path.realpath('./compile'),
                  errors_are_fatal=errors_are_fatal[pid],
                  verbosity=verbosity[pid],
                  debug=debug[pid])
    for f in flist:
        pathname = os.path.join(dir,f)
        if f in ('CVS', 'penvironment.d'):
            continue
        try:
            mode = os.stat(pathname)[ST_MODE]
            if S_ISDIR(mode) and f[0] != '.':
                compile_dir_and_recurse(pathname,level+1,force)
                os.chdir(dir)
        except OSError, e:
            if verbosity[pid] > 1:
                print "WARNING:  Skipping", pathname, "due to", e

##
# Compile all code in, and below, <code>dir</code>.
# First, all non-Python code is compiled recusively by invoking all the
# ./compile commands, then all the Python code is compiled.
# @param dir The root directory for the compile.
# @param force 
# @default 0
# @keyword 'debug'
# default 0
# @keyword 'verbosity'
# default 1
# @keyword 'errors_are_fatal'
# default 0
# 
def compile_dir(dir,force=0, **keywords):
    global debug
    global verbosity
    global errors_are_fatal
    key = os.getpid()
    debug[key] = 0
    verbosity[key] = 1
    errors_are_fatal[key] = 0
    map_globals = {'debug':debug,
                   'verbosity':verbosity,
                   'errors_are_fatal':errors_are_fatal}
    try:
        keys = keywords.keys()
        for keyword in ('debug','verbosity','errors_are_fatal'):
            if keywords.has_key(keyword):
                keys.remove(keyword)
                map_globals[keyword][key] = keywords[keyword]
        if keys:
            raise TypeError,\
                  'compile_dir() got an unexpected keyword argument %s' % \
                  keys[0]
        compile_dir_and_recurse(dir,0,force)
        compileall.compile_dir(dir,ddir=os.path.basename(dir),force=force)
    finally:
        del debug[key]
        del verbosity[key]
        del errors_are_fatal[key]
