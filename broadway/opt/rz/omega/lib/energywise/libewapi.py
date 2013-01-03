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
import os

from ctypes import *

c_int8_p = POINTER(c_int8)
c_uint16_p = POINTER(c_uint16)
c_uint32_p = POINTER(c_uint32)
c_uint8_p = POINTER(c_uint8)

def _no_conv(ewp):
    return None
def ewp_int8_as_int(ewp):
    return cast(ewp,c_int8_p).contents.value
def ewp_int16_x11_as_ints(raw):
    return None
def ewp_int32_x11_as_ints(raw):
    return None
def ewp_sockaddr_to_str(sockaddr_p):
    _buffer = create_string_buffer('\0'*36, 36)
    ewp_sender_to_str(sockaddr_p, _buffer, c_int(_buffer._length_))
    return _buffer.value
def ewp_uint16_as_int(ewp):
    return cast(ewp,c_uint16_p).contents.value
def ewp_uint32_as_int(ewp):
    return cast(ewp,c_uint32_p).contents.value
def ewp_uint8_as_int(ewp):
    return cast(ewp,c_uint8_p).contents.value

ewp_as_string = string_at

CPEX_DEFAULT_PORT = 43440

class AttributeEnum(c_int):
    def __init__(self,name,value):
        self._ae_name = name
        self._ae_hash = (name,value)
        c_int.__init__(self,value)
        return
    def __str__(self):
        return self._ae_name
    def __repr__(self):
        return "%s(%d)" % (self._ae_name, self.value)
    def __int__(self):
        return self.value
    def __hash__(self):
        return hash(self._ae_hash)
    def __cmp__(self,other):
        return int(self) - int(other)

def ENUM(name,value):
    globals()[name] = AttributeEnum(name,value)

ENUM('EW_ATTRIBUTE_TYPE_ENERGYWISE_ID', 1)
ENUM('EW_ATTRIBUTE_TYPE_ROLE', 2)
ENUM('EW_ATTRIBUTE_TYPE_DOMAIN', 3)
ENUM('EW_ATTRIBUTE_TYPE_NAME', 4)
ENUM('EW_ATTRIBUTE_TYPE_KEYWORDS', 5)
ENUM('EW_ATTRIBUTE_TYPE_ERROR_STRING', 6)
ENUM('EW_ATTRIBUTE_TYPE_UNITS', 7)
ENUM('EW_ATTRIBUTE_TYPE_USAGE', 8)
ENUM('EW_ATTRIBUTE_TYPE_LEVEL', 9)
ENUM('EW_ATTRIBUTE_TYPE_IMPORTANCE', 10)
ENUM('EW_ATTRIBUTE_TYPE_ENTITY_TYPE', 11)
ENUM('EW_ATTRIBUTE_TYPE_REPLY_TO', 12)
ENUM('EW_ATTRIBUTE_TYPE_NEIGHBOR', 13)
ENUM('EW_ATTRIBUTE_TYPE_NEIGHBOR_COUNT', 14)
ENUM('EW_ATTRIBUTE_TYPE_NANNY_VECTOR', 15)
ENUM('EW_ATTRIBUTE_TYPE_DELTA_VECTOR', 16)
ENUM('EW_ATTRIBUTE_TYPE_USAGE_CALIBER', 17)
ENUM('EW_ATTRIBUTE_TYPE_USAGE_VECTOR', 18)
ENUM('EW_ATTRIBUTE_TYPE_QUERY_TIMEOUT', 19)
ENUM('EW_ATTRIBUTE_TYPE_RECURRENCE', 20)
ENUM('EW_ATTRIBUTE_TYPE_DEVICE_TYPE', 21)

SHA_DIGEST_LENGTH = 20
SHA_DIGEST_CLASS = c_char*SHA_DIGEST_LENGTH

from mpx.lib.exceptions import MpxException

class EnergywiseApiError(MpxException):
    pass

class EConnectFailed(EnergywiseApiError):
    pass

class ESumFailed(EnergywiseApiError):
    pass

class ELibNotLoaded(EnergywiseApiError):
    pass

class AttributeValue(dict):
    _conversion_map = {
        EW_ATTRIBUTE_TYPE_ENERGYWISE_ID:ewp_sockaddr_to_str,
        EW_ATTRIBUTE_TYPE_ROLE:string_at,
        EW_ATTRIBUTE_TYPE_DOMAIN:string_at,
        EW_ATTRIBUTE_TYPE_NAME:string_at,
        EW_ATTRIBUTE_TYPE_KEYWORDS:string_at,
        EW_ATTRIBUTE_TYPE_ERROR_STRING:string_at,
        EW_ATTRIBUTE_TYPE_UNITS:ewp_int8_as_int,
        EW_ATTRIBUTE_TYPE_USAGE:ewp_uint16_as_int,
        EW_ATTRIBUTE_TYPE_LEVEL:ewp_uint8_as_int,
        EW_ATTRIBUTE_TYPE_IMPORTANCE:ewp_uint8_as_int,
         # Not Exposed, 4 byte enum
        EW_ATTRIBUTE_TYPE_ENTITY_TYPE:_no_conv,
        EW_ATTRIBUTE_TYPE_REPLY_TO:ewp_sockaddr_to_str,
         # Not Exposed, struct
        EW_ATTRIBUTE_TYPE_NEIGHBOR:_no_conv,
        # Not working
        EW_ATTRIBUTE_TYPE_NEIGHBOR_COUNT:ewp_uint16_as_int,
        EW_ATTRIBUTE_TYPE_NANNY_VECTOR:ewp_uint32_as_int,
        EW_ATTRIBUTE_TYPE_DELTA_VECTOR:ewp_int32_x11_as_ints,
         # 4 bytes, energywise_usage_caliber_t 
        EW_ATTRIBUTE_TYPE_USAGE_CALIBER:_no_conv,
        EW_ATTRIBUTE_TYPE_USAGE_VECTOR:ewp_int16_x11_as_ints,
        EW_ATTRIBUTE_TYPE_QUERY_TIMEOUT:ewp_uint8_as_int,
        # variable length, energywise_recurrence_t
        EW_ATTRIBUTE_TYPE_RECURRENCE:_no_conv,
        EW_ATTRIBUTE_TYPE_DEVICE_TYPE:string_at,
        }
    def __init__(self, attribute, raw, length):
        self.attribute = attribute
        self['attribute'] = attribute
        self.raw = raw
        self['raw'] = raw
        self.length = length
        self['length'] = length
        value = self._conversion_map.get(attribute,_no_conv)(raw)
        self.value = value
        self['value'] = value
        return

LIBEWAPI_FILE = os.path.join(os.path.dirname(__file__), "_libewapi.so")
def _libew_not_loaded(*args,**kw):
    raise ELibNotLoaded(LIBEWAPI_FILE)

energywise_addGetAttribute = _libew_not_loaded
energywise_closeSession = _libew_not_loaded
energywise_createSession = _libew_not_loaded
energywise_createCollectQuery = _libew_not_loaded
energywise_createSumQuery = _libew_not_loaded
energywise_execQuery = _libew_not_loaded
energywise_getAttributeFromRowByType =  _libew_not_loaded
energywise_getNextRow = _libew_not_loaded
energywise_queryResults = _libew_not_loaded
energywise_releaseQuery = _libew_not_loaded
energywise_releaseResult = _libew_not_loaded
energywise_utl_composeKey = _libew_not_loaded
energywise_utl_createUuid = _libew_not_loaded
# @fixme look at anything without a wrapper to unwrap "special" values.
try:
    _libew=cdll.LoadLibrary(os.path.join(LIBEWAPI_FILE))
    energywise_addGetAttribute = (
        lambda *args: _libew.energywise_addGetAttribute(*args)
        )
    energywise_closeSession = (
        lambda *args: _libew.energywise_closeSession(*args)
        )
    def energywise_createSession(dest, port, uuid, key, timeout):
        return _libew.energywise_createSession(c_char_p(dest), c_int(port),
                                               uuid, key,
                                               c_int(key.contents._length_),
                                               c_int(timeout))
   
    def energywise_createCollectQuery(domain, importance):
        return _libew.energywise_createCollectQuery(c_char_p(domain),
                                                    c_int(importance))
    def energywise_createSumQuery(domain, importance):
        return _libew.energywise_createSumQuery(c_char_p(domain),
                                                c_int(importance))
    energywise_execQuery = lambda *args: _libew.energywise_execQuery(*args)
    energywise_getAttributeFromRowByType = (
        lambda *args: _libew.energywise_getAttributeFromRowByType(*args)
        )
    def energywise_getAttributeFromRowByType(row, attribute):
        length = c_int(0)
        raw = _libew.energywise_getAttributeFromRowByType(
            row, attribute, byref(length)
            )
        return AttributeValue(attribute, raw, length.value)
    energywise_getNextRow  = lambda *args: _libew.energywise_getNextRow(*args)
    energywise_releaseQuery = (
        lambda *args: _libew.energywise_releaseQuery(*args)
        )
    energywise_queryResults = (
        lambda *args: _libew.energywise_queryResults(*args)
        )

    def energywise_releaseResult(result_set):
            return _libew.energywise_releaseResult(result_set)
    
    def energywise_utl_composeKey(shared_secret, uuid):
        digest = pointer(SHA_DIGEST_CLASS())
        _libew.energywise_utl_composeKey(
            c_char_p(shared_secret), c_int(len(shared_secret)),
            uuid, digest, c_int(SHA_DIGEST_LENGTH)
            )
        return digest
    def energywise_utl_createUuid():
        uuid = create_string_buffer(36)
        _libew.energywise_utl_createUuid(uuid)
        return uuid
except:
    from mpx.lib import msglog
    msglog.exception()

ADDRESS_FILE = os.path.join(os.path.dirname(__file__), "_address.so")
def _address_not_loaded(*args,**kw):
    raise ELibNotLoaded(LIBEWAPI_FILE)

ewp_sender_to_str = _address_not_loaded
try:
    _address=cdll.LoadLibrary(os.path.join(ADDRESS_FILE))
    ewp_sender_to_str = lambda *args: _address.ewp_sender_to_str(*args)
    def ew_memcpy(dst, src, length):
        return _address.ew_memcpy(dst, src, length)
    def ew_buffer():
        return _address.ew_buffer()
except:
    from mpx.lib import msglog
    msglog.exception()
