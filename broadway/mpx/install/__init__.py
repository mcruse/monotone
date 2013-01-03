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
# Functions and classes that support installing Broadway packages.

from _lib import *
from _dag import *
import filesystem

from tools.pfileinfo import FileInfo, ECommand
from mpx.lib.configure import as_boolean

def get_file_type(filename):
    get = FileInfo(('pfileinfo','-v','0',
                    'type','--type-only',property_name,filename))
    result = get.run()
    if result != 0:
        return None
    result = get.get_stdout_msg()
    if len(result) and result[-1] == '\n':
        result = result[:-1]
    return result

def get_file_property(filename, property_name):
    get = FileInfo(('pfileinfo','-v','0',
                    'get','--value-only',property_name,filename))
    try:
        result = get.run()
    except ECommand:
        return None
    if result != 0:
        return None
    result = get.get_stdout_msg()
    if len(result) and result[-1] == '\n':
        result = result[:-1]
    return result

def set_file_property(filename, property_name, property_value):
    set = FileInfo(('pfileinfo','-v','0',
                    'set',property_name,property_value,filename,filename))
    result = set.run()
    return result

def get_package_property(filename):
    return get_file_property(filename, 'package')

import re
_RE_VERSION=re.compile(".*Mediator Framework \(tm\) "
                       # (Group 1 (Group 2))
                       "([0-9]+(\.[0-9]+)+)"
                       # (((Group 3 (Group 4 (Group 5)(Group 6)))
                       "(((\.dev\.|\.build\.|,\s*build\s*)([0-9]+))|)"
                       ".*")
_VERSION_GROUP = 1
_BUILD_GROUP   = 6

def _extract_version(line):
    version = None
    match = _RE_VERSION.match(line)
    if match:
        version = match.group(_VERSION_GROUP)
        build   = match.group(_BUILD_GROUP)
        if build:
            version = "%s.build.%s" %(version, build)
    return version

def get_version_property(filename):
    try:
        version = get_file_property(filename, 'version')
    except ECommand:
        version = None
    if version is None and os.path.isfile(filename):
        # Support versions < 1.3...
        f = open(filename,'r')
        try:
            for line in f.xreadlines():
                version = _extract_version(line)
                if version is not None:
                    break
        finally:
            f.close()
    return version

def get_upgradeable_property(filename):
    return get_file_property(filename, 'upgradeable')

def isfile_upgradeable(filename):
    upgradeable = 1
    if os.path.exists(filename):
        # See if the file's been acquired by another package, or
        # replaced by the end user.
        upgradeable = get_upgradeable_property(filename)
        if upgradeable is not None:
            upgradeable = upgradeable.lower()
            try:
                upgradeable = as_boolean(upgradeable)
            except:
                upgradeable = 0
        else:
            # Typically, this indicates that a user has overwritten
            # the file.  But we need to survive the 1.2 to 1.3
            # transition...
            upgradeable = 1
            version = get_version_property(filename)
            if version is not None:
                major, minor, revision, build = (0,0,0,0)
                version = version.split('.')
                if len(version) > 2:
                    if version[-2] == 'build':
                        build = version.pop() # Get build number.
                        version.pop()         # Remove 'build'
                if len(version):
                    major = int(version.pop(0))
                    if len(version):
                        minor = int(version.pop(0))
                        if len(version):
                            revision = int(version.pop(0))
                if (major > 1) or (major == 1 and minor > 2):
                    # The file should have had the upgradeable property,
                    # assume that the file has been changed.
                    upgradeable = 0
            else:
                # No version information, this file's been overwritten
                # by the user.
                upgradeable = 0
    return upgradeable

##
# Replace every reference to a property inclosed in ${} with the value
# of the property.
def replace_property_references(filename):
    import os
    import re
    import mpx
    regex = re.compile("^(.*)\${(mpx.properties.[A-Z0-9a-z_]+)}(.*)$")
    pid = os.getpid()
    temp_file = "%s.%s" % (filename,pid)
    input_file = open(filename, 'r')
    output_file = open(temp_file,'w')
    for line in input_file.xreadlines():
        match = regex.match(line)
        while match:
            line = "%s%s%s\n" % (match.group(1),
                                 eval(match.group(2)),
                                 match.group(3))
            match = regex.match(line)
        output_file.write(line)
    input_file.close()
    output_file.close()
    os.rename(temp_file, filename)
    return
