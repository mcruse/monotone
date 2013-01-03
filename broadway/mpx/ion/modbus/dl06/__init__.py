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
from mpx.lib.modbus.base import crc as _crc
from struct import pack as _pack
from array import array as _array

from dl06 import DL06

##
# Introducing the "Managed device."  A managed device is a device that
# is built by, or programmed by Envenergy.  Typically, managed devices
# are used for applications that require more (or different) I/O than
# the Mediator provides.
#
class ManagedDevice:
    pass # It's a concept, not an object...

class ManagedDeviceVersion:
    def __init__(self, product_code, major_version, minor_version, revision):
        self.product_code = product_code
        self.major_version = major_version
        self.minor_version = minor_version
        self.revision = revision
        return
    def crc(self):
        encoding = _array('b', _pack('!4H',
                                     self.product_code, self.major_version,
                                     self.minor_version, self.revision))
        return _crc(encoding)

class SupportedManagedDevice:
    def __init__(self, product_code, major_version, name, description):
        self.product_code = product_code
        self.major_version = major_version
        self.name = name
        self.description = description
        return
    def __str__(self):
        return (
            "%s:\n    product code: %s\n    major version: %s\n\n%s"
            % (self.name, self.product_code,
               self.major_version, self.description))

DL06_CT8_PC4 = SupportedManagedDevice(1,1,"DL06-CT8-PC4", """\
    DL06 programmed with Envenergy's DL06-CT8-PC4 logic and configured with
    F0-04AD-1 option modules in slots 1 and 2.

    The DL06-CT8-PC4 logic provides access to all 20 DIs and 16 DOs on the
    DL06.  The first for DIs can be used as counters as well as simple
    digital inputs.

    The F0-04AD-1 option modules are access via programing that supports
    four CTs per option module.  The additional logic provides a basic
    metering values calculated from the CTs.""")

##
# Class used to maintain a "database" of supported managed devices.
class SupportedManagedDevices:
    def __init__(self):
        ##
        # Dictionary of dictionaries.  The key is the envenergy product code
        # and the value is a dictionary of SupportedManagedDevice, using
        # the major_version as a key.
        self._products = {}
        return
    ##
    # @param product A SupportedManagedDevice instance to add to the list of
    #                supported products.
    def add(self, product):
        if not self._products.has_key(product.product_code):
            self._products[product.product_code] = {}
        version_dictionary = self._products[product.product_code]
        if version_dictionary.has_key(product.major_version):
            raise EInUse
        version_dictionary[product.major_version] = product
        return
    def find(self, product_code, major_version):
        return self._products[product_code][major_version]
    def __str__(self):
        result = ''
        for version_dictionary in self._products.values():
            for product in version_dictionary.values():
                if result:
                    result = "%s\n%s" % (result, str(product))
                else:
                    result = str(product)
        return result

SUPPORTED_MANAGED_DEVICES = SupportedManagedDevices()
SUPPORTED_MANAGED_DEVICES.add(DL06_CT8_PC4)
