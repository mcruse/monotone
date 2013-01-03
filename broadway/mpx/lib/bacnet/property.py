"""
Copyright (C) 2002 2003 2004 2005 2006 2007 2010 2011 Cisco Systems

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

import time
import array
import types
import copy

from _exceptions import *
from mpx.lib.exceptions import EInvalidValue

from mpx.lib.bacnet import sequence, tag, data, datatype
from mpx.lib.bacnet.datatype import *
from mpx.lib.bacnet.datatype import _enum, _ListAsTags, _data as UnknownDataType
from mpx.lib.bacnet.object import object_types
from mpx.lib.bacnet._bacnet import write_property_g3, read_property_g3, read_property_multiple_g3, _read_property_multiple_g3, recv_callback_helper
from mpx.ion import Result
from mpx.lib import msglog
from mpx.lib.bacnet.sequence import _OPTIONAL as OPTIONAL
from mpx.lib import Callback
from mpx.lib.bacnet.tsstrings import tsenum, est, data_type_enum, object_property_data as opd, property_ids, BACnetObjectTypeStr

debug = 0
COMM3_TIMEOUT = 15.0
                
data_enum_2_class = {
    "PTYPE_BOOLEAN"                   : datatype.BACnetBoolean,
    "PTYPE_UNSIGNEDINT"               : datatype.BACnetUnsigned,
    "PTYPE_SIGNEDINT"                 : datatype.BACnetInteger,
    "PTYPE_REAL"                      : datatype.BACnetReal,
    "PTYPE_OCTETSTRING"               : datatype.BACnetOctetString,
    "PTYPE_CHARSTRING"                : datatype.BACnetCharacterString,
    "PTYPE_BITSTRING"                 : datatype._bit_string,
    "PTYPE_ENUMERATED"                : datatype._enum,
    "PTYPE_DATE"                      : datatype.BACnetDate,
    "PTYPE_TIME"                      : datatype.BACnetTime,
    "PTYPE_BACNET_OBJECT_ID"          : datatype.BACnetObjectIdentifier,
    "PTYPE_BACNET_EVENT_STATE"        : datatype.BACnetEventState,
    "PTYPE_BACNET_DATE_TIME"          : datatype.BACnetDateTime,
    "PTYPE_BACNET_DATE_RANGE"         : datatype.BACnetDateRange,
    "PTYPE_BACNET_OBJ_PROP_REFERENCE" : datatype.BACnetObjectPropertyReference,
    "PTYPE_BACNET_SERVICES_SUPPORTED" : datatype.BACnetServicesSupported,
    "PTYPE_BACNET_OBJ_TYPES_SUPPORTD" : BACnetObjectTypesSupported,
    "PTYPE_BACNET_STATUS_FLAGS"       : datatype._bit_string,
    "PTYPE_BYTESTRING2"               : datatype._data,
    "PTYPE_APPLICATION_MEMBER"        : datatype._sequence,
     }

str_2_id = {}
str_2_id.update(dict(zip(property_ids.values(), property_ids.keys()))) #should work without the dict() function but doesn't

#present_value_data_types = {
        #0:BACnetReal,
        #1:BACnetReal,
        #2:BACnetReal,
        #3:BACnetBinaryPV,
        #4:BACnetBinaryPV,
        #5:BACnetBinaryPV,
        #6:BACnetBoolean,
        #7:BACnetUnsigned,
        #8:None,
        #9:None,
        #10:None,
        #11:BACnetReadAccessResult,
        #12:BACnetLifeSafetyState,
        #13:BACnetUnsigned,
        #14:BACnetUnsigned,
        #15:None,
        #16:None,
        #17:None, #figure this one out later
        #18:None, #has no present value
        #19:BACnetUnsigned,
        #20:None,
        #21:BACnetLifeSafetyState,
        #22:BACnetLifeSafetyState
       #}
                            

## _Property is the base class for all BACnet property types
# BACnet Properties are owned by BACnet Objects which in turn are owned by BACnet Devices
# When a subclass of _Property is instantiated, 
#@params device_number = the device number in which the property resides
#@params object_type = the number or string that identifies the type of object "self" is a property of...
#                      @see object_types above for a map of objecte type strings and numbers
#@params object_number = the number identifying this instance of the owning object

#identifier is the property number
#data_type is the class of the data the property holds
#owner is the object to be notified when updates occur to the properties value
#_data holds the BACnet Data type object for the property
#ttl time to live for cached values
#last_get_time the time the last request was made for this properties value
#last_result the last python type result of a node get() function
#average_read_time the running average of the time between get()s
#_object_indentifier a BACnet Object Identifier for this property
#_property_reference aBACnet property reference object
#_value the python value of the _data object
#_tags the tag representation of the data object of this property 
vendor_mods = None
class _Property:
    def __init__(self, identifier, object_type, object_number, value=None, \
                 data_type_class=None, **keywords):
        com3 = None
        _ts_enum = None
        if type(object_type) == types.StringType:
            object_type = obj_types[object_type] #convert to number from string
            
        if type(identifier) == types.StringType: # property name passed in
            if str_2_id.has_key(identifier):
                property_name = identifier
                identifier = str_2_id[identifier]

        if debug: print 'init property %s %s ' % (str(object_type), str(identifier),)

        vendor_id = None
        if keywords.has_key('vendor_id'):
            vendor_id = keywords['vendor_id']
        data_type_id, array_limit, is_array, is_list, ucm_page = opd[object_type][identifier][:5]
        if data_type_class is None:
                try:
                    data_type_class = data_enum_2_class[data_type_enum[data_type_id]]
                except:
                    if debug: print 'unable to look up data class in property'
                    msglog.exception()
                    data_type_class = None
        if is_array:
            self.__class__=_Array
        if is_list:
            self.__class__=_List
        self.T_out = 3.0
        self._comm3segment = None
        if ucm_page:
            self._comm3segment = ucm_page
            self.T_out = COMM3_TIMEOUT #comm3 devices are slower
        self.enum_string_map = None
        if data_type_class:
           if issubclass(data_type_class, _enum): #use class map as default
               self.enum_string_map = data_type_class._enumeration_string_map
        if tsenum.has_key((object_type,identifier,)):
            self.enum_string_map = est[tsenum[(object_type,identifier)]] #table has priorty over class
        #look up data type enum and then class
        # if enum or bitstring, need to init string table

        # now set up all the instance variables
        
        self.identifier = identifier
        self.data_type = data_type_class
        self.object_type = object_type
        self.object_number = object_number
        self.property_tuple = (object_type, object_number, identifier)
        self.device = None
        self.vendor_id = vendor_id
        self._data = None
        self._value = None
        self.cache = None
        self.ttl=0
        self.last_result = None
        self.last_get_time = None
        self.average_read_time = self.ttl
        self.owner = None
        self._object_identifier = None
        self._property_reference = None
        self._tags = None
        self._table_based = 1

    def encoding(self):
        self._data.encoding
    def __getattr__(self, attribute):
        if attribute == 'object_identifier':
            if self._object_identifier is None:
                self._object_identifier = BACnetObjectIdentifier(self.object_type, self.object_instance)
            return self._object_identifier
        if attribute == 'object_property_reference':
            if self._property_reference is None:
                self._property_reference = BACnetObjectPropertyReference( \
                        object_id=self.object_identifier,
                        property_id = self.identifier).encoding
            return self._property_reference
        if attribute == 'encoding':
            return self.encoding()
        if attribute == 'data':
            return self._get_native_data()
        if attribute == 'value':
            return self._get_value()
        if attribute == 'tags':
            return self.encode_value()
        if attribute == 'value_string':
            return self._get_value_string()
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'object_identifier':
            raise EPermission, 'object_identifier is read-only'
        if attribute == 'object_property_reference':
            raise EPermission, 'object_property_reference is read-only'
        if attribute == 'data':
            return self._set_native_data(value)
        if attribute == 'value':
            self._set_value(value)
            return
        #if attribute == 'tags':
            #return self._set_native_data(value)
        self.__dict__[attribute] = value
    def as_tags(self, index = None):
        return self.data.as_tags()  #see __getattr__ above for how "data" attribute is magically updated
    def _set_tags(self, value):
        self._tags = value
        self._value = None
    def _get_value(self):
        if self._value is None:
            if not self._data is None:
                self._value = self._data.value
        return self._value
    def _get_value_string(self):
        return str(self._get_value())
    def _set_value(self, value):
        self._value = None #force conversion via data_type = value
        self._data = self.data_type(value, string_map=self.enum_string_map, owner=self)
        self._tags = None
    def _get_native_data(self):
        if debug: print 'get native data :', self._value, self._data
        if self._data is None:
            if not self._value is None: 
                if debug: print 'convert python data to bacnet data object'
                self._data = self.data_type(self._value, string_map=self.enum_string_map, owner=self)
        return self._data
    def encode_value(self):
        return self.data.as_tags()
    def _set_native_data(self, value):
        self._data = value
    def get_from(self, device, skipCache=0):
        return self.get_result_from(device, skipCache).value
    def get_result_from(self, device, skipCache=0, **keywords):
        self.device = device #to help with property reference
        #performs a read property either directly or through the caching mechanism
        if self.last_get_time:
            self.average_read_time = ((self.average_read_time * TIME_CONSTANT) + 
                                      (time.time() - self.last_get_time)) / (TIME_CONSTANT + 1)
        callback = None
        if keywords.has_key('callback'):
            keywords['callback'].callback(self.get_result_callback)
            callback = 1
        if keywords.has_key('T_OUT'):
            self.T_out = keywords['T_OUT']
        if self.owner and callback is None: #like an ion
            if debug: print '^^^^^^^^^^^^^^^^ get from cache.  skip?:', str(skipCache)
            self.last_result = self.owner.cache.get(self, skipCache, self.T_out)
            if debug: print 'cache result was: ', str(self.last_result)
            if self.last_result:
                if debug: print ' assign value to self._value'
                if isinstance(self.last_result.value.value, float):
                    self._value = round(self.last_result.value.value, 4)
                else:
                    self._value = self.last_result.value.value
        else:
            if debug: print 'get directly'
            try:
                    r = read_property_g3(device, self.property_tuple, self.T_out, **keywords)
                    if isinstance(r, Callback):
                        return r #used as flag
                    if debug: print '  response: ', r, r.property_value
                    v = r.property_value
                    self.decode(v)
            except BACnetNPDU, e:
                    self._value = str(e) #print the error message without the call back
            self.last_result = Result()
            if isinstance(self._value.value, float):
                self.last_result.value = round(self._value.value, 4)
            else:
                self.last_result.value = self._value.value
            self.last_result.timestamp = time.time()
        
        return self.last_result

    def get_result_callback(self, rp):  #called all the way from the TSM callback upon completion
        try:
            if isinstance(rp, Exception):
                raise rp
            v = rp.property_value
            self.decode(v)
            self.last_result = Result()
            self.last_result.value = self._value
            self.last_result.timestamp = time.time()
            return self.last_result
        except Exception, e: #any other exception
            return e
        except:
            import sys
            return Exception(sys.exc_info()[0])

    def _can_get_multiple(self):
        return 1
    def set(self, device, priority=None):
        if debug: print '~~~~~~~ Property Set : ', str(self), priority
        p = self.property_tuple
        t = self.data.as_tags()
        if debug: 
            print '           prop tuple: ', str(p)
            print '           tags      : ', str(t)
            print '           data:       ', str(self.data)
            print '           data type:  ', type(self.data)
        return write_property_g3(device, p, t, priority)
    def is_binary_pv(self):
        if self.data_type == BACnetBinaryPV:
            return 1
        return 0
    def decode(self, value):
        self._data = None #force creation of new data object.  Subscription manager compare didn't work because OLD 
        # instance of value was the same object as the new one and decoding changed the value in the old one
        if self._data is None: #we have not yet created the data object for this property
            if debug: print '!!!!!!!!!!!!!!!!!!! ',self.data_type, type(value), str(value)
            self._data = self.data_type(decode=value, string_map=self.enum_string_map, owner=self)
        else:  #we had one from before
            self._data.decode_from_tags(value)
        self._value = self._data # do NOT change to "...=self._data.value": prevents auto-conv for enums
        if debug: print 'Property decode', str(self._value)
        return self
    def __str__(self):
        return self._get_value_string()
    def __repr__(self):
        # BEGIN: mevans
        if isinstance(self.value, Exception):
            return repr(self.value)
        # END: mevans
        return repr(str(self))


# Helper function: used at least by Trane Custom Properties (eg BACnetPropertyWeeklySchedule):
    def is_array(self):
        return 0
    def get_array_length(self):
        return 0
    def str_property_id(self):
        return property_ids[self.identifier]
def str_recursive(s, v):
    if (type(v) == types.TupleType) or (type(v) == types.ListType):
        s += '['
        for i in v:
            s = str_recursive(s, i)
        s += '],'
    else:
        s += str(v)
        s += ','
    return s

class _Array(_Property):
    #_value is list of simple python values
    #_data is list of BACnet data object
    def decode(self, values):
        #self._hidden_tags = values
        self._data = []
        self._value = []
        if self.data_type.can_decode_from_list: #class variable
            #print 'can decode lists'
            dt = self.data_type(string_map=self.enum_string_map, owner=self) #create a blank one to call helper fucntion
            seqs = dt.decode_list_of(values)
            #print 'did decode lists'
            for s in seqs:
                #print 'decoding a sequence'
                d = self.data_type(string_map=self.enum_string_map, owner=self)
                try:
                    d.decode_from_sequence(s)
                    self._value.append(d.value)
                except Exception, ex:
                    d = ex
                self._data.append(d)
        else:
            for v in values:
               if debug: print 'decode array = ', str(v)
               d = self.data_type(decode=[v], string_map=self.enum_string_map, owner=self)
               self._data.append(d)
               self._value.append(d.value)
        return self
    def _get_value_string(self): #similar to, but not as hard core as repr
        answer = '['
        self._get_value()
        if type(self._value) != types.ListType:
            return str(self._value)
        #return self.__repr__()
        for v in self.value: #if this is changed back to _value, we lose the specialized str-ing datatypes have
            if self.enum_string_map:
                if hasattr(v, '_has_magnitude_interface') and (v._has_magnitude_interface == 1):
                    answer += repr(str(v)) + ', '
                else:
                    answer += repr(v) + ', '
            elif self.data_type == BACnetCharacterString:
                answer += v + ', '
            else:
                answer += str(v) + ', '
        if answer[-2:] == ', ':
            answer = answer[:-2]
        answer += ']'
        return answer
    def __repr__(self):
        if type(self._value) != types.ListType:
            return repr(self._value)
        # BEGIN: mevans
        # Um, why not just do this?
        # return repr(self._data)
        # END: mevans
        answer = '['
        for v in self._data:
            if self.enum_string_map:
                if hasattr(v, '_has_magnitude_interface') and (v._has_magnitude_interface == 1):
                    answer += str({'num':v.as_magnitude(),'str':str(v)}) + ', '
                else:
                    answer += repr(v) + ', '
            elif hasattr(v, '_has_magnitude_interface') and (v._has_magnitude_interface == 1):
                answer += str(v.as_magnitude()) +', '
            elif self.data_type == BACnetCharacterString:
                answer += repr(v) + ', '
            else:
                answer += str(v) + ', '
        if answer[-1] == ' ':
            answer = answer[:-2]
        answer += ']'
        return answer
    def _get_native_data(self):
        if debug: print 'get native data :', self._value, self._data
        if self._data is None:
            if not self._value is None: 
                if debug: print 'convert python data to bacnet data object'
                self._data = []
                for v in self._value:
                    if hasattr(v,'as_sequence'):
                        self._data.append(v.as_sequence())
                    else:
                        self._data.append(self.data_type(v, string_map=self.enum_string_map, owner=self))
        return self._data
    def _set_value(self, values):
        self._value = [] # clear existing list of datatype objects
        self._data = None # clear list of sequence objects
        self._tags = None # clear list of tags
        if type(values) == types.StringType:
            values = eval(values)
            assert type(values) == types.ListType, 'values = %s' % values
            for i in range(len(values)):
                self._value.append(self.data_type(values[i], string_map=self.enum_string_map, owner=self)) # so, datatype ctor must understand strings (poss nested)
        elif type(values) == types.ListType:
            self._value = values
#            _Property._set_value(self, values)
        else:
            raise EInvalidValue('values', values, 'Must be list or string-ized list')
    def as_tags(self, index = None):
        #print index
        t = []
        if index is None:
            for d in self.data:
                t.extend(d.encoding)
            return t
        if index == 0:
            #print self.data
            #print len(self.data)
            #print tag.UnsignedInteger(len(self.data))
            return [tag.UnsignedInteger(len(self.data))]
        return self.data[index-1].as_tags()
    def get_result_from(self, device, skipCache=0, **keywords):
        #first try the normal way to get all at once, if that fails do each element seperately
        if (skipCache == 0) and self.last_result: #we've been here before
            if (time.time() + self.ttl) < self.last_result.timestamp:
                return self.last_result
        if keywords.has_key('T_OUT'):
            self.T_out = keywords['T_OUT']
        if not hasattr(self, '_segmentation_error'): self._segmentation_error = 0
        if self._segmentation_error == 0:
            if self.vendor_id != 2: #trane always uses rpm
                try:
                    answer = _Property.get_result_from(self, device, skipCache)
                    if isinstance(answer.value, BACnetException):
                        raise answer.value
                    return answer
                #why do these not work???
                #except BACnetAbort, e:
                    #if e.npdu.reason != 4:
                        #raise
                #except BACnetError, e:
                    #pass #try segmented read for all errors
                except BACnetException, e:
                    #print 'bacnet exception'
                    pass
                #except Exception, e:
                    #print 'some other error'
                    #print e
                    #print e.__class__.__name__
                    #raise
                #print 'try array method 1,2'
            self._segmentation_error = 1

        answer = []
        if self._segmentation_error == 1:    
            #get length of list
            len = read_property_g3(device, self.property_tuple+(0,), self.T_out)
            self._array_length = len.property_value[0].value
            self._segmentation_error = 2
        if self._segmentation_error == 2:
            #print 'start array method 2'
            #try rpm first
            #comm3 text strings are assumed to be static and we only read them one time per framework startup
            if self._comm3segment is not None:
                if self.data_type == BACnetCharacterString:
                    if self.last_result is not None:
                        #self.owner.set_batch_manager(None) #may not make much difference but once we've read it, don't need to use batching
                        #the previous line did not work, may need to throw EBadBatch exception
                        #print '#### array static value ####', self.last_result
                        if keywords.has_key('callback'):
                            keywords['callback'].unwind_callbacks(self.last_result)
                            return keywords['callback']
                        return self.last_result
            try:
                pids = []
                pid = self.property_tuple[2]
                if self._array_length > 1:
                    for i in range(1, self._array_length+1):
                        pids.append((pid, i,))
                    props = (self.property_tuple[0], self.property_tuple[1], tuple(pids))
                    if keywords.has_key('callback'):
                        keywords['callback'].callback(self.get_result_callback)
                    rars = _read_property_multiple_g3(device, [props], self.T_out, **keywords)
                    if isinstance(rars, Callback):
                        return rars #used as flag to indcate callback method will be used
                    rar = rars.pop(0)
                    lrs = copy.copy(rar.list_of_results)
                    while(lrs):
                        lr = lrs.pop(0)
                        pe = lr.property_access_error
                        pv = lr.property_value
                        if not isinstance(pv, OPTIONAL):
                            answer.extend(pv)
                        elif not isinstance(pe, OPTIONAL):
                            raise pe
                    #print 'array method 2 completed'
            except Exception, e:
                #print 'try array method 3'
                #print str(e)
                if self.vendor_id != 2:
                    self._segmentation_error = 3
                else:
                    raise e #trane arrays only use rpm method
        if self._segmentation_error == 3:
            for i in range(1, self._array_length+1):
                obj_tag = read_property_g3(device, self.property_tuple+(i,), self.T_out).property_value[0]
                answer.append(obj_tag)
            #print 'array method 3 completed'

        self.decode(answer)
        self.last_result = Result()
        self.last_result.value = self._value
        self.last_result.timestamp = time.time()
        return self.last_result

    def get_result_callback(self, rars):  #called all the way from the TSM callback upon completion
        answer = []
        try:
            if isinstance(rars, Exception):
                raise rars
            rar = rars.pop(0)
            lrs = copy.copy(rar.list_of_results)
            while(lrs):
                lr = lrs.pop(0)
                pe = lr.property_access_error
                pv = lr.property_value
                if not isinstance(pv, OPTIONAL):
                    answer.extend(pv)
                elif not isinstance(pe, OPTIONAL):
                    raise pe
            self.decode(answer)
            self.last_result = Result()
            self.last_result.value = self._value
            self.last_result.timestamp = time.time()
            return self.last_result
        except Exception, e: #any other exception
            r = Result(e,time.time())
            r.value = e
            r.timestamp = time.time()
            return r
    def set(self, device, priority=None):
        p = list(self.property_tuple + (1,))
        for m in range(0,len(self.data)):
            elem = self.data[m]
            t = elem.encoding
            p[3] = m+1
            write_property_g3(device, p, t, priority)
        #t = self.datat.as_tags()
       # Clear cache for this property, to force update of value after set:
        if self.owner and self.owner.cache.has_key(self):
            del self.owner.cache.cache[self]
        #return write_property_g3(device, p, t, priority)
    def _default_numeric_type(self):
        answer = []
        if type(self._value) != types.ListType:
            return self._value
        for v in self._data:
            d = v
            if hasattr(v, '_default_numeric_type'):
                d = v._default_numeric_type()
            answer.append(d)
        return answer
    #def _can_get_multiple(self):
        #return 0
    def is_array(self):
        return 1
    def get_array_length(self, device):
        if isinstance(self.value, types.ListType):
            return len(self._value)
        l = read_property_g3(device, self.property_tuple+(0,), self.T_out)
        return l.property_value[0].value

class _List(_Array):
    #_value is list of simple python values
    #_data is list of BACnet data object
    def as_tags(self, index = None):
        t = []
        if index:
            raise EInvalidValue('index', index, 'must be none for BACnet list object')
        for d in self.data:
            t.extend(d.encoding)
        return t
    def set(self, device, priority=None):
        p = self.property_tuple
        t = self.as_tags() #lists get written all at once
       # Clear cache for this property, to force update of value after set:
        if self.owner and self.owner.cache.has_key(self):
            del self.owner.cache.cache[self]
        return write_property_g3(device, p, t, priority)
    def get_result_from(self, device, skipCache=0,**keywords):
        #first try the normal way to get all at once, if that fails do each element seperately
        if (skipCache == 0) and self.last_result: #we've been here before
            if (time.time() + self.ttl) < self.last_result.timestamp:
                return self.last_result

        return _Property.get_result_from(self, device, skipCache, **keywords)
    def is_array(self):
        return 0 #since it always (should) read as a single property, not use rpm

class BACnetPropertyDescription(_Property):
    def __setattr__(self, attribute, value):
        if attribute == 'value':
            if type(value) == 'str':
                value = ANSI_String(value)
        _Property.__setattr__(self, attribute, value)
    pass
class BACnetPropertyPresentValue(_Property):
    def as_tags(self, index = None):
        if self.data.value is None:
            self.data.value = 0
        return _Property.as_tags(self, index)

#build a reverse look up of properties who have a class defined in this module
prop_from_id = {}

