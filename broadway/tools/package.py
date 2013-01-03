"""
Copyright (C) 2002 2010 2011 Cisco Systems

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
import os, sys
from stat import *
from string import split
import string
import re
import sys

def expr(regex,name,line):
    str = "^%s([+|=])(.*)"%name
    r = re.compile(str).search(line)
    if r:
        if r.groups()[0] == '+' and regex:
            return regex + '|' + r.groups()[1]
        else:
            return r.groups()[1]
    else:
        return regex

class PackageExpr:

    def __init__(self,parent):
        self.include = None
        self.exclude = None
        if parent:
            self.rinclude = parent.rinclude
            self.rexclude = parent.rexclude
        else:
            self.rinclude = None
            self.rexclude = None
            

    def apply(self,fname):
        f = open(fname)
        line = f.readline()
        while line:
            self.include = expr(self.include,"include",line)
            self.exclude = expr(self.exclude,"exclude",line)
            self.rinclude = expr(self.rinclude,"rinclude",line)
            self.rexclude = expr(self.rexclude,"rexclude",line)
            line = f.readline()
        f.close()

    def re(self,regex,str):
        if (regex and re.compile(regex).search(str)):
            return 1
        else:
            return None

    def is_included(self,f):
        if (self.re(self.rinclude,f) or self.re(self.include,f)):
            if (self.re(self.rexclude,f) or self.re(self.exclude,f)):
                return None
            else:
                return 1
        else:
            return None


def _add_to_manifest( package, dir, manifest ):
    if os.path.basename(dir) in ("penvironment.d", "CVS"):
        #
        # Skip CVS, penvironment.d and their contents.
        #
        return
    # If the current directory contains a .flist file for the package...
    fname = os.path.join( dir, package + '.flist' )
    if os.path.isfile( fname ):
        
        # Read the list of relative file names from the .flist file.
        finclude = open( fname )
        files = finclude.readlines()
        finclude.close()
        
        # Replace the leading "./" in the directory name with the name of the
        # current directory.
        thisdir = os.path.join( os.path.split( os.getcwd() )[1], dir[2:] )
        
        # Add the path names of the files to the manifest.
        for file in files:
            file = file.strip()
            
            # Skip blanks lines and comments
            if len( file ) and file[0] != '#':
                manifest.append( os.path.join( thisdir, file.strip() ) )
    
    # For each file in the current directory...
    for f in os.listdir( dir ):
        
        # Ignore files that start with a period.
        if f[0] == '.':
            continue
            
        # If the file is a directory then scan it for a .flist file.
        pathname = os.path.join( dir, f )
        if os.path.isdir( pathname ):
            _add_to_manifest( package, pathname, manifest )
    
def get_manifest( package, dir ):
    # Initial list of file names.
    manifest = []
    _add_to_manifest( package, dir, manifest )
    return manifest


def walktree(packages, dir, expr, manifest):
    '''recursively descend the directory rooted at dir,
       calling checking expression for non directory files'''

    expr = PackageExpr(expr)

    for package in packages:
        fname = os.path.join(dir,".%s.pkg"%package)
        if (os.path.exists(fname)):
            expr.apply(fname)
        
    for f in os.listdir(dir):
        pathname = os.path.join(dir,f)
        mode = os.stat(pathname)[ST_MODE]
        if S_ISDIR(mode):
            if f[0] != '.':
                walktree(packages,pathname, expr, manifest)
        else:
            if expr.is_included(pathname):
                manifest.append(os.path.split(os.getcwd())[-1]+
                                '/'+pathname[2:])
    return manifest
