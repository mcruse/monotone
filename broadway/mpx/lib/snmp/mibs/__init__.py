"""
Copyright (C) 2007 2010 2011 Cisco Systems

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
# mpx.lib.snmp.mibs:
#
# MORE INFO ON CREATING COMPILED MIBS IN:
#    ~mevans/pysnmp-experiments/Panduit-MIBs-1/PANDUIT.sh
#
# This "module" contains Python representations of MIBs generated via the
# build-pysnmp-mib utility (part of the pysnmp-4.1.* package and that also
# requires smidump, part of the libsmi package).
#
# Using the modules contained in this package requires the following in the
# runtime environment:
#
# pysnmp: e.g.  pysnmp-4.1.7a.tar.gz
# pysnmp-mibs: e.g.  pysnmp-mibs-0.0.5a.tar.gz
# pyasn: e.g.  pyasn1-0.0.6a.tar.gz
#
# To build a Pytohn MIB requires the the following package.  These are not
# required in the runtime environment, unless we decide to compile MIBs on the
# Mediator itself.
#
# libsmi: e.g.  libsmi-0.4.5.tar.gz
#
# The compiled MIB should be named the same as the MIB name in the DEFINITIONS
# declaration of the actual MIB.  E.g. the powernet388.mib file contains the
# declaration "PowerNet-MIB DEFINITIONS ::= BEGIN", so the compiled file should
# be named PowerNet-MIB.py.
#
# EXAMPLE CREATION OF COMPILED MIB:
#
#   $ build-pysnmp-mib -o PowerNet-MIB.py powernet388.mib
#
#
# OTHER NOTES:
#
# The compiled MIB modules are here only as a quick convienience.  Given the
# mechanisms that PySNMP provides, there is no need for the compiled MIBs to be
# in the broadway tree and actually probably should be in /var/mpx/snmp/mibs or
# something like that.
#
# More evidence that the Python modules belong elsewhere is that .pyc files
# don't work, PySNMP uses execfile to load the modules which does not support
# .pyc files, only .py files.
#
# PYSNMP_MIB_DIR is a bit limitted in that it only supports a single
# directory.  And setPath, etc, only operates on instances which I think is
# problematic for "oneline" commands.

# Importing this module will initialize the PYSNMP_MIB_DIR so the
# pysnmp.smi.MibBuilder class will find these compiled MIBs.

import os

if os.environ.has_key('PYSNMP_MIB_DIR'):
    # Development HACK that overrides the environment.  Evil.
    del os.environ['PYSNMP_MIB_DIR']

if not os.environ.has_key('PYSNMP_MIB_DIR'):
    os.environ['PYSNMP_MIB_DIR'] = (
        # @note PySNMP seems to require the '.' on the end of the path as it
        #       strips final element from the path...
        os.path.join(os.path.realpath(os.path.split(__file__)[0]), '.')
        )

del os
