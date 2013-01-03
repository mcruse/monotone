"""
Copyright (C) 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012 Cisco Systems

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

from mpx.lib.bacnet._exceptions import *
from mpx.lib.exceptions import EInvalidValue, EPermission
from mpx.lib import EnumeratedDictionary, EnumeratedValue
from mpx.lib.bacnet import sequence, tag, data
from mpx.lib.bacnet.sequence import CHOICE, OPTIONAL

debug = 0

##
# properties currently not supported:
#PTYPE_APPLICATION_MEMBER

class _ListAsTags:
    def __init__(self, list):
        self.value = list

##
# base class for all bacnet non-primitive data types
#
# provides automatic conversion between python value vs tagged encoded
# expression of a bacnet value converts from one representation to the
# other lazily upon request.  May be initailzed with an engineering value
# upon init.  Use _data_object.value for engineering value.
# str, int, float
# as_tags
# .data_object is primitive bacnet data module type object
# .value is python data
# .encoding is tagged expression of object
# assigning to .value or .data_object forces conversion to other mode upon a reference

class _data:
    can_decode_from_list = 0 #cannot
    _has_magnitude_interface = 1
    def __init__(self, value=None, **keywords ):
        if value == 'None': value = None
        self._value = value
        self._data_object = value  #default data object is simply the python object
        if keywords.has_key('decode'):
            if value != None:
                raise EInvalidValue('The decode keyword is mutually ' +
                                    'exclusive with the value parameter')
            self.decode(keywords['decode'])
    def encode(self):
        return self.as_tags()
    def decode(self, buffer):
        if debug: print buffer, type(buffer)
        if type(buffer) == types.StringType:
            return self.decode_from_string(buffer)
        if type(buffer) == types.ListType or type(buffer) == types.TupleType:
            return self.decode_from_tags(buffer)
        if type(buffer) == types.InstanceType:
            if debug: print 'Instance type error'
            if buffer.__class__ == sequence._OPTIONAL:
                raise sequence.ETagMissing(self.__class__.__name__)
            return self.decode_from_sequence(buffer)
        raise EInvalidValue('bacnet decode exception', str(type(buffer)), str(buffer))
    def __repr__(self):
        # BEGIN: mevans
        if isinstance(self.value, Exception):
            return repr(self.value)
        # END: mevans
        if self._has_magnitude_interface:
            if self.value is not None:
                return str(self._default_numeric_type())
        return repr(str(self))
    def decode_from_string(self, string):
        self.decode_from_tags(tag.decode(string).value)
    def decode_from_tags(self, tags):
        self._data_object=tags[0].value
        self._value = None
        return self._data_object
    def decode_from_sequence(self, seq):
        self._data_object = seq #let subclasses add their 2 cents worth before conversion
        self._value = None #force lazy conversion
        return self._data_object
    def as_tags(self): #usually overloaded by subclass
        if self.data_object is None:
            return [tag.Null()]
        return [self._data_object.encoding]
    def __getattr__(self, attribute):
        if attribute == 'encoding':
            return self.as_tags()
        if attribute == 'value':
            if self._value is None:
                if not self._data_object is None:
                    self.value_from_data_object()
            return self._value
        if attribute == 'data_object':
            if self._data_object is None:
                if not self._value is None:
                    self.data_object_from_value()
            return self._data_object
        try: 
            return self.__dict__[attribute]
        except KeyError: 
            raise AttributeError(attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'value':
            if value == 'None': #this is not used in any property
                value = None
            self._value = value
            self._data_object = None
            return
        if attribute == 'data_object':
            self._data_object = value
            self._value = None
            return
        if attribute == 'can_decode_from_list':
            raise EPermission('read only', 'can_decode_from_list',
                              'datatype._data')
        self.__dict__[attribute] = value
    def value_from_data_object(self):
        self._value = self._data_object
    def data_object_from_value(self):
        self._data_object = self._value
    def __str__(self):
        return str(self.value)
    def __int__(self):
        return int(self.value)
    def __float__(self):
        return float(self.value)
    def _default_numeric_type(self):
        if self.value is None:
            return None
        return self.__float__()
    def as_magnitude(self):
        # BEGIN: mevans
        if isinstance(self.value, Exception):
            return self.value
        # END: mevans
        return self._default_numeric_type()
    def __eq__(self, o):
        if self.__class__ != o.__class__:
            return self.value == o
        return self.value == o.value
    def __ne__(self, o):
        return not self.__eq__(o)
    def __lt__(self, o):
        if self.__class__ != o.__class__:
            return self.value < o
        return self.value < o.value
    def __gt__(self, o):
        if self.__class__ != o.__class__:
            return self.value > o
        return self.value > o.value
class _sequence(_data):
    _has_magnitude_interface = 0
    # def __init__(self, value=None, **keywords):
        # _data.__init__(self, None, **keywords)
        # #self._has_magnitude_interface = 0
        # if self._data_object is None:
            # self._data_object=self
    def __getattr__(self, attribute):
        if attribute == 'value':
            if self._value is None:
                self.value_from_data_object()
            return self._value
        if attribute == 'data_object':
            if self._data_object is None:
                if self._value is None:
                    self.value_from_data_object()
                self.data_object_from_value()
            return self._data_object
        return _data.__getattr__(self, attribute)
    def data_object_from_value(self):
        pass
    def decode_from_tags(self, tags):
        answer = []
        if len(tags) == 1: #may allow simpler decode
            t=tags[0]
            if not t.is_constructed:
                return _data.decode_from_tags(tags)
        #need fuller decoding
        for t in tags:
            if t.is_application:
                answer.append({'type':'application', 'number':t.number, 'value':t.value})
            elif t.is_constructed:
                answer.append({'type':'constructed', 'number':t.number, 'value':self.decode_from_tags(t.value)})
            elif t.is_context:
                answer.append({'type':'context', 'number':t.number, 'value':t.value})
            else:
                answer.append({'type':'unknown'})
        self.data_object=answer
        return answer
    def as_tags(self): #usually overloaded by subclass
        if self.data_object is None:
            return [tag.Null()]
        return self._data_object.encoding #sequences produce lists of tags
    def __setattr__(self, attribute, value):
        if attribute == 'value':
            self._value = value
            self.data_object_from_value()
        if attribute == 'data_object':
            self._data_object = value
            self.value_from_data_object()
        self.__dict__[attribute] = value
    def __repr__(self):
        d = self.as_dict()
        #hack to give BACnetOjbectIdentifiers a repr
        for k in d.keys():
            if repr(type(d[k])) == "<type 'BACnetObjectIdentifier'>":
                d[k] = (d[k].object_type, d[k].instance_number,)
        #end hack
        return repr(d)
    def __eq__(self, o):
        return 0  #by default sequences are never equal to each other
    def as_dict(self):
        d = {}
        d['__base__'] = 'datatype'
        d['__class__'] = class_path_of(self)
        d['str'] = self.__str__()
        return d

class _choice(_sequence):
    def __init__(self, choice_value=None, choice_name=None, **keywords):
        self.choice_name=choice_name
        _sequence.__init__(self, None, **keywords)
        if keywords.has_key('decode'): #need some processing to get choice name
            self.find_choice_name()
        self._value=choice_value
    def find_choice_name(self):
        #find the active choice
        for entry in self._data_object._sequence_map.values():
            if hasattr(self._data_object, entry.name): #may found it
                if getattr(self._data_object, entry.name) != sequence.CHOICE:
                    self.choice_name=entry.name
                    return

    def decode_from_sequence(self, seq):
        _sequence.decode_from_sequence(self,seq)
        self.find_choice_name()
    def value_from_data_object(self):
        self._value = getattr(self._data_object,self.choice_name)
    def data_object_from_value(self):
        raise ENotImplemented('implemented by subclass')
    #def as_tags(self):
        #return getattr(self.data_object,self.choice_name).as_tags()
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['choice_name'] = self.choice_name
        d['choice_value'] = str(self.value)
        return d
class _enum(_data):
    _enumeration_string_map = {}
    def __init__(self, value=None, **keywords):
        if keywords.has_key('string_map'):
            map = keywords['string_map']
            if map:
                self._enumeration_string_map = map
        value = self._check_value(value)
        _data.__init__(self, value, **keywords)
        #self._has_magnitude_interface = 0
    def __setattr__(self, attribute, value):
        if attribute == 'value': # or attribute == '_value':
            value = self._check_value(value)
        _data.__setattr__(self, attribute, value)
        if attribute == 'value':
            if not self._value is None:
                if not self._enumeration_string_map.has_key(self._value):
                    raise EInvalidValue('enumeration value not allowed', value)
    def _check_value(self, value):
        if (value is not None) and len(self._enumeration_string_map):
            num = value
            if type(value) == types.StringType: #convert enum word to int
                if debug: print 'CONVERT STRING TO ENUM INT in init'
                if value == 'None': #this is not used in any property
                    return None
                num = key_at_value(self._enumeration_string_map, value)
                if num is None:
                    try:
                        num = int(float(value)) #maybe we have a string of the number
                    except:
                        raise EInvalidValue('string not found in map: ', value)
            if not self._enumeration_string_map.has_key(num):
                #raise EInvalidValue('enumeration value not allowed', value)
                return EnumeratedValue(int(num), str(num))
            #why was this commentted out ?
            return EnumeratedValue(int(num), self._enumeration_string_map[int(num)])
        return value
    def as_tags(self):
        d = self.data_object
        if d is None:
            if debug: print 'ENUM type as_tags returning null tag'
            return [tag.Null()] #an empty list to clear an override
            #raise EInvalidValue('enumeration value is None', self)
        return [tag.Enumerated(d)]
    def __str__(self):
        if self._enumeration_string_map.has_key(self.value):
            return self._enumeration_string_map[self.value]
        if not self.value is None:
            return str(self.value) + ' unknown'
        return 'None'
    def is_enum(self):
        return 1
    def enum(self):
        return {'num':self.as_magnitude(),
                'str':str(self),
                '_has_magnitude_interface':1
               }
    def __repr__(self):
        # BEGIN: mevans
        if isinstance(self.value, Exception):
            return repr(self.value)
        # END: mevans
        if self.value is None:
            return str(None)
        if self._enumeration_string_map:
            if hasattr(self, '_has_magnitude_interface') and (self._has_magnitude_interface == 1):
                return str({'num':self.as_magnitude(),'str':str(self)})
        return _data.__repr__(self)
    def _default_numeric_type(self):
        if self.value is None:
            return None
        return int(self.value)
class _unsigned(_data):
    def __init__(self, value=None, **keywords):
        if value == 'None': value = None
        if value is not None:
            value = int(value) #convert any strings to ints
        _data.__init__(self, value, **keywords)
    def as_tags(self):
        if self.data_object is None:
            return [tag.Null()]
        return [tag.UnsignedInteger(self.data_object)]
    def _default_numeric_type(self):
        return int(self.value)
class _string(_data):
    _has_magnitude_interface = 0
    def __init__(self, value=None, **keywords):
        _data.__init__(self, value, **keywords)
        #self._has_magnitude_interface = 0
        if type(value) == types.StringType:
            self._data_object = data.ANSI_String(value) #convert the d.o. to our default
    def as_tags(self):
        if self.data_object is None:
            return [tag.Null()]
        return [tag.CharacterString(self.data_object)]
    def decode_from_tags(self, tags):
        self.data_object=tags[0].value
    def value_from_data_object(self):
        self._value = self._data_object.character_string
    def data_object_from_value(self):
        self._data_object = data.ANSI_String(self._value)
    def __repr__(self):
        return repr(self.value)
class _bit_string(_data):
    _has_magnitude_interface = 0
    _bit_string_map={}
    def __init__(self, bit_string=None, **keywords):
        _data.__init__(self, bit_string, **keywords)
        self._lookup = None #reverse lookup map
        if keywords.has_key('string_map'):
            map = keywords['string_map']
            if map:
                self._bit_string_map = map
        self._has_magnitude_interface = 0
        if bit_string: #create data object from value
            if type(bit_string) == types.StringType:
                bit_string = eval(bit_string) #convert string to list or tuple
            self.value = tuple(bit_string)  #needs to be a tuple type
        #if not self._value is None:
            #if len(self.value) > len(self._bit_string_map):
                #raise EInvalidValue('BACnet datatype', 'too many elements in bit string', str(self._bit_string_map))
    def as_tags(self):
        if self.value is None:
            return [tag.Null()]
        return [tag.BitString(data.BitString(self.value))]
    def decode_from_tags(self, tags):
        self.data_object=tags[0].value
    def __str__(self):
        bit_string = array.array('c')
        i = 0
        if self.value is None:
            return 'None'
        for b in self.value:
            if i < len(self._bit_string_map):
                bit_string.extend(array.array('c', self._bit_string_map[i]))
            else:
                bit_string.append('?')
            bit_string.append('=')
            if b:
                bit_string.append('1')
            else:
                bit_string.append('0')
            i = i + 1
            if i < len(self.value):
                bit_string.extend(array.array('c', ', '))
        return bit_string.tostring()
    def value_from_data_object(self):
        self._value = self._data_object.bits
    def data_object_from_value(self):
        self._data_object = data.BitString(self._value)
    def get_bit(self, name):
        if self._lookup is None:
            if self._bit_string_map:
                self._lookup = {}
                for k,v in self._bit_string_map.items():
                    self._lookup[v]=k
        try:
            return self.value[self._lookup[name]]
        except:
            return None
class BACnetOctetString(_data):
    _has_magnitude_interface = 0
    def as_tags(self):
        if self.data_object is None:
            return [tag.Null()]
        return [tag.OctetString(self.data_object)]
    def __str__(self):
        return string.join(map(lambda b: "%02X" % ord(b), self.value), '-')
    def __repr__(self):
        return repr(self.__str__())

class BACnetCharacterString(_string):
    pass

class BACnetEngineeringUnits(_enum):
    _enumeration_string_map={
         0:'square_meters',
         1:'square_feet', 
         2:'milliamperes', 
         3:'amperes', 
         4:'ohms', 
         5:'volts', 
         6:'kilovolts', 
         7:'megavolts', 
         8:'volt_amperes', 
         9:'kilovolt_amperes', 
         10:'megavolt_amperes', 
         11:'volt_amperes_reactive', 
         12:'kilovolt_amperes_reactive', 
         13:'megavolt_amperes_reactive', 
         14:'degrees_phase', 
         15:'power_factor', 
         16:'joules', 
         17:'kilojoules', 
         18:'watt_hours', 
         19:'kilowatt_hours', 
         20:'btus', 
         21:'therms', 
         22:'ton_hours', 
         23:'joules_per_kilogram_dry_air', 
         24:'btus_per_pound_dry_air', 
         25:'cycles_per_hour', 
         26:'cycles_per_minute', 
         27:'hertz', 
         28:'grams_of_water_per_kilogram_dry_air', 
         29:'percent_relative_humidity', 
         30:'millimeters', 
         31:'meters', 
         32:'inches', 
         33:'feet', 
         34:'watts_per_square_foot', 
         35:'watts_per_square_meter', 
         36:'lumens', 
         37:'luxes', 
         38:'foot_candles', 
         39:'kilograms', 
         40:'pounds_mass', 
         41:'tons', 
         42:'kilograms_per_second', 
         43:'kilograms_per_minute', 
         44:'kilograms_per_hour', 
         45:'pounds_mass_per_minute', 
         46:'pounds_mass_per_hour', 
         47:'watts', 
         48:'kilowatts', 
         49:'megawatts', 
         50:'btus_per_hour', 
         51:'horsepower', 
         52:'tons_refrigeration', 
         53:'pascals', 
         54:'kilopascals', 
         55:'bars', 
         56:'pounds_force_per_square_inch', 
         57:'centimeters_of_water', 
         58:'inches_of_water', 
         59:'millimeters_of_mercury', 
         60:'centimeters_of_mercury', 
         61:'inches_of_mercury', 
         62:'degrees_Celsius', 
         63:'degrees_Kelvin', 
         64:'degrees_Fahrenheit', 
         65:'degree_days_Celsius', 
         66:'degree_days_Fahrenheit', 
         67:'years', 
         68:'months', 
         69:'weeks', 
         70:'days', 
         71:'hours', 
         72:'minutes', 
         73:'seconds', 
         74:'meters_per_second', 
         75:'kilometers_per_hour', 
         76:'feet_per_second', 
         77:'feet_per_minute', 
         78:'miles_per_hour', 
         79:'cubic_feet', 
         80:'cubic_meters', 
         81:'imperial_gallons', 
         82:'liters', 
         83:'us_gallons', 
         84:'cubic_feet_per_minute', 
         85:'cubic_meters_per_second', 
         86:'imperial_gallons_per_minute', 
         87:'liters_per_second', 
         88:'liters_per_minute', 
         89:'us_gallons_per_minute', 
         90:'degrees_angular', 
         91:'degrees_Celsius_per_hour', 
         92:'degrees_Celsius_per_minute', 
         93:'degrees_Fahrenheit_per_hour', 
         94:'degrees_Fahrenheit_per_minute', 
         95:'no_units', 
         96:'parts_per_million', 
         97:'parts_per_billion', 
         98:'percent', 
         99:'percent_per_second', 
         100:'per_minute', 
         101:'per_second', 
         102:'psi_per_degree_Fahrenheit', 
         103:'radians', 
         104:'revolutions_per_minute', 
         105:'currency1', 
         106:'currency2', 
         107:'currency3', 
         108:'currency4', 
         109:'currency5', 
         110:'currency6', 
         111:'currency7', 
         112:'currency8', 
         113:'currency9', 
         114:'currency10', 
         115:'square_inches', 
         116:'square_centimeters', 
         117:'btus_per_pound', 
         118:'centimeters', 
         119:'pounds_mass_per_second', 
         120:'delta_degrees_Fahrenheit', 
         121:'delta_degrees_Kelvin', 
         122:'kilohms', 
         123:'megohms', 
         124:'millivolts', 
         125:'kilojoules_per_kilogram', 
         126:'megajoules', 
         127:'joules_per_degree_Kelvin', 
         128:'joules_per_kilogram_degree_Kelvin', 
         129:'kilohertz', 
         130:'megahertz', 
         131:'per_hour', 
         132:'milliwatts', 
         133:'hectopascals', 
         134:'millibars', 
         135:'cubic_meters_per_hour', 
         136:'liters_per_hour', 
         137:'kilowatt_hours_per_square_meter', 
         138:'kilowatt_hours_per_square_foot', 
         139:'megajoules_per_square_meter', 
         140:'megajoules_per_square_foot', 
         141:'watts_per_square_meter_degree_kelvin', 
         142:'cubic_feet_per_second', 
         143:'percent_obscuration_per_foot', 
         144:'percent_obscuration_per_meter',
         }
    pass
class BACnetAction(_enum):
    _enumeration_string_map={
         0:'direct',
         1:'reverse',
         }
class BACnetObjectType(_enum):
    _enumeration_string_map={
        0:'analog_input',
        1:'analog_output',
        2:'analog_value',
        3:'binary_input',
        4:'binary_output',
        5:'binary_value',
        6:'calendar',
        7:'command',
        8:'device',
        9:'event_enrollment',
        10:'file',
        11:'group',
        12:'loop',
        13:'multi_state_input',
        14:'multi_state_output',
        15:'notification_class',
        16:'program',
        17:'schedule',
        18:'averaging',
        19:'multi_state_value',
        20:'trend_log',
        21:'life_safety_point',
        22:'life_safety_zone',
        }
class BACnetObjectIdentifier(_data):
    def __init__(self, object_type=None, instance_number=None, **keywords):
        if keywords.has_key('decode'):
            _data.__init__(self, **keywords)
        else:
            if instance_number is None:
                _data.__init__(self, data.BACnetObjectIdentifier(object_type))
            else:
                _data.__init__(self, data.BACnetObjectIdentifier(object_type, instance_number))
        self._value = self.data_object.id               
        self.object_type=self.data_object.object_type
        self.instance_number=self.data_object.instance_number
    def as_tags(self):
        return [tag.BACnetObjectIdentifier(self.data_object)]
    def value_from_data_object(self):
        self._value = self._data_object.id
        self.object_type=self._data_object.object_type
        self.instance_number=self._data_object.instance_number
    def data_object_from_value(self):
        self._data_object = data.BACnetObjectIdentifier(self._value)
    def __str__(self):
        return hex(self.value)
    def _default_numeric_type(self):
        return self.__int__()
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.value == o.value
        return 0
class BACnetDeviceStatus(_enum):
    _enumeration_string_map={
        0:'operational',
        1:'operational_read_only',
        2:'download_required',
        3:'download_in_progress',
        4:'non_operational',
        5:'backup_in_progress',
        }
class BACnetSegmentation(_enum):
    _enumeration_string_map={
        0:'segmented_both',
        1:'segmented_transmit',
        2:'segmented_receive',
        3:'no_segmentation',
        }
class BACnetVTClass(_enum):
    _enumeration_string_map={
        0:'default_terminal',
        1:'ansi_x3_64',
        2:'dec_vt52',
        3:'dec_vt100',
        4:'dec_vt220',
        5:'hp_700_94',
        6:'ibm_3130',
        }
class BACnetEventState(_enum):
    _enumeration_string_map={
        0:'normal',
        1:'fault',
        2:'offnormal',
        3:'high_limit',
        4:'low_limit',
        5:'life_safety_alarm',
        }
class BACnetEventType(_enum):
    _enumeration_string_map={
        0:'change_of_bitstring',
        1:'change_of_state',
        2:'change_of_value',
        3:'command_failure',
        4:'floating_limit',
        5:'out_of_range',
        6:'complex_event_type',
        7:'buffer_ready',
        8:'change_of_life_safety',
        }
class BACnetFileAccessMethod(_enum):
    _enumeration_string_map={
        0:'record_access',
        1:'stream_access',
        }
class BACnetLifeSafetyMode(_enum):
    _enumeration_string_map={
        0:'off',
        1:'on',
        2:'test',
        3:'manned',
        4:'unmanned',
        5:'armed',
        6:'disarmed',
        7:'prearmed',
        8:'slow',
        9:'fast',
        10:'disconnected',
        11:'enabled',
        12:'disabled',
        13:'automatic_release_disabled',
        14:'default',
        }
class BACnetLifeSafetyOperation(_enum):
    _enumeration_string_map={
        0:'none',
        1:'silence',
        2:'silence_audible',
        3:'silence_visual',
        4:'reset',
        5:'reset_alarm',
        6:'reset_fault',
        }
class BACnetLifeSafetyState(_enum):
    _enumeration_string_map={
        0:'quiet',
        1:'pre_alarm',
        2:'alarm',
        3:'fault',
        4:'fault_pre_alarm',
        5:'fault_alarm',
        6:'not_ready',
        7:'active',
        8:'tamper',
        9:'test_alarm',
        10:'test_active',
        11:'test_fault',
        12:'test_fault_alarm',
        13:'holdup',
        14:'duress',
        15:'tamper_alarm',
        16:'abnormal',
        17:'emergency_power',
        18:'delayed',
        19:'blocked',
        20:'local_alarm',
        21:'general_alarm',
        22:'supervisory',
        23:'test_supervisory',
        }
class BACnetMaintenance(_enum):
    _enumeration_string_map={
        0:'none',
        1:'periodic_test',
        2:'need_service_operational',
        3:'need_service_inoperative', 
        }
class BACnetSilencedState(_enum):
    _enumeration_string_map={
        0:'unsilenced',
        1:'audible_silenced',
        2:'visible_silenced',
        3:'all_silenced',
        }
class BACnetNotifyType(_enum):
    _enumeration_string_map={
        0:'alarm',
        1:'event',
        2:'ack_notification',
        }
class BACnetPolarity(_enum):
    _enumeration_string_map={
        0:'normal',
        1:'reverse',
        }
class BACnetProgramRequest(_enum):
    _enumeration_string_map={
        0:'ready',
        1:'load',
        2:'run',
        3:'halt',
        4:'restart',
        5:'unload',
        }
class BACnetProgramState(_enum):
    _enumeration_string_map={
        0:'idle',
        1:'loading',
        2:'running',
        3:'waiting',
        4:'halted',
        5:'unloading',
        }
class BACnetProgramError(_enum):
    _enumeration_string_map={
        0:'normal',
        1:'load_failed',
        2:'internal',
        3:'program',
        4:'other',
        }
class BACnetReliability(_enum):
    _enumeration_string_map={
        0:'no_fault_detected',
        1:'no_sensor',
        2:'over_range',
        3:'under_range',
        4:'open_loop',
        5:'shorted_loop',
        6:'no_output',
        7:'unreliable_other',
        }
class BACnetBinaryPV(_enum):
    _enumeration_string_map={
        0:'inactive',
        1:'active',
        }
class BACnetPropertyIdentifier(_enum):
    _enumeration_string_map={
        0:'acked_transitions',
        1:'ack_required',
        2:'action',
        3:'action_text',
        4:'active_text',
        5:'active_vt_sessions',
        6:'alarm_value',
        7:'alarm_values',
        8:'all',
        9:'all_writes_successful',
        10:'apdu_segment_timeout',
        11:'apdu_timeout',
        12:'application_software_version',
        13:'archive',
        14:'bias',
        15:'change_of_state_count',
        16:'change_of_state_time',
        17:'notification_class',
        18:'deleted',
        19:'controlled_variable_reference',
        20:'controlled_variable_units',
        21:'controlled_variable_value',
        22:'cov_increment',
        23:'datelist',
        24:'daylight_savings_status',
        25:'deadband',
        26:'derivative_constant',
        27:'derivative_constant_units',
        28:'description',
        29:'description_of_halt',
        30:'device_address_binding',
        31:'device_type',
        32:'effective_period',
        33:'elapsed_active_time',
        34:'error_limit',
        35:'event_enable',
        36:'event_state',
        37:'event_type',
        38:'exception_schedule',
        39:'fault_values',
        40:'feedback_value',
        41:'file_access_method',
        42:'file_size',
        43:'file_type',
        44:'firmware_revision',
        45:'high_limit',
        46:'inactive_text',
        47:'in_process',
        48:'instance_of',
        49:'integral_constant',
        50:'integral_constant_units',
        51:'issue_confirmed_notifications',
        52:'limit_enable',
        53:'list_of_group_members',
        54:'list_of_object_property_references',
        55:'list_of_session_keys',
        56:'local_date',
        57:'local_time',
        58:'location',
        59:'low_limit',
        60:'manipulated_variable_reference',
        61:'maximum_output',
        62:'max_apdu_length_accepted',
        63:'max_info_frames',
        64:'max_master',
        65:'max_pres_value',
        66:'minimum_off_time',
        67:'minimum_on_time',
        68:'minimum_output',
        69:'min_pres_value',
        70:'model_name',
        71:'modification_date',
        72:'notify_type',
        73:'number_of_APDU_retries',
        74:'number_of_states',
        75:'object_identifier',
        76:'object_list',
        77:'object_name',
        78:'object_property_reference',
        79:'object_type',
        80:'optional',
        81:'out_of_service',
        82:'output_units',
        83:'event_parameters',
        84:'polarity',
        85:'present_value',
        86:'priority',
        87:'priority_array',
        88:'priority_for_writing',
        89:'process_identifier',
        90:'program_change',
        91:'program_location',
        92:'program_state',
        93:'proportional_constant',
        94:'proportional_constant_units',
        95:'protocol_conformance_class',
        96:'protocol_object_types_supported',
        97:'protocol_services_supported',
        98:'protocol_version',
        99:'read_only',
        100:'reason_for_halt',
        101:'recipient',
        102:'recipient_list',
        103:'reliability',
        104:'relinquish_default',
        105:'required',
        106:'resolution',
        107:'segmentation_supported',
        108:'setpoint',
        109:'setpoint_reference',
        110:'state_text',
        111:'status_flags',
        112:'system_status',
        113:'time_delay',
        114:'time_of_active_time_reset',
        115:'time_of_state_count_reset',
        116:'time_synchronization_recipients',
        117:'units',
        118:'update_interval',
        119:'utc_offset',
        120:'vendor_identifier',
        121:'vendor_name',
        122:'vt_classes_supported',
        123:'weekly_schedule',
        124:'attempted_samples',
        125:'average_value',
        126:'buffer_size',
        127:'client_cov_increment',
        128:'cov_resubscription_interval',
        129:'current_notify_time',
        130:'event_time_stamps',
        131:'log_buffer',
        132:'log_device_object_property',
        133:'log_enable',
        134:'log_interval',
        135:'maximum_value',
        136:'minimum_value',
        137:'notification_threshold',
        138:'previous_notify_time',
        139:'protocol_revision',
        140:'records_since_notification',
        141:'record_count',
        142:'start_time',
        143:'stop_time',
        144:'stop_when_full',
        145:'total_record_count',
        146:'valid_samples',
        147:'window_interval',
        148:'window_samples',
        149:'maximum_value_timestamp',
        150:'minimum_value_timestamp',
        151:'variance_value',
        152:'active_cov_subscriptions',
        153:'backup_failure_timeout',
        154:'configuration_files',
        155:'database_revision',
        156:'direct_reading',
        157:'last_restore_time',
        158:'maintenance_required',
        159:'member_of',
        160:'mode',
        161:'operation_expected',
        162:'setting',
        163:'silenced',
        164:'tracking_value',
        165:'zone_members',
        166:'life_safety_alarm_values',
        167:'max_segments_accepted',
        168:'profile_name',
        }
class BACnetEventTransitionBits(_bit_string):
    _bit_string_map={
        0:'to_offnormal',
        1:'to_fault',
        2:'to_normal',
        }
class BACnetDaysOfWeek(_bit_string):
    _bit_string_map={
        0:'monday',
        1:'tuesday',
        2:'wednesday',
        3:'thursday',
        4:'friday',
        5:'saturday',
        6:'sunday',
        }
class BACnetStatusFlags(_bit_string):
    _bit_string_map={
        0:'in-alarm',
        1:'fault',
        2:'overridden',
        3:'out-of-service',
        }
class BACnetServicesSupported(_bit_string):
    _bit_string_map={
        0:'AcknowledgeAlarm',
        1:'ConfirmedCOVNotification',
        2:'ConfirmedEventNotification',
        3:'GetAlarmSummary',
        4:'GetEnrollmentSummary',
        5:'SubscribeCOV',
        6:'AtomicReadFile',
        7:'AtomicWriteFile',
        8:'AddListElement',
        9:'RemoveListElement',
        10:'CreateObject',
        11:'DeleteObject',
        12:'ReadProperty',
        13:'ReadPropertyConditional',
        14:'ReadPropertyMultiple',
        15:'WriteProperty',
        16:'WritePropertyMultiple',
        17:'DeviceCommunicationControl',
        18:'ConfirmedPrivateTransfer',
        19:'ConfirmedTextMessage',
        20:'ReinitializeDevice',
        21:'VtOpen',
        22:'VtClose',
        23:'VtData',
        24:'Authenticate',
        25:'RequestKey',
        26:'I_Am',
        27:'I_Have',
        28:'UnconfirmedCOVNotification',
        29:'UnconfirmedEventNotification',
        30:'UnconfirmedPrivateTransfer',
        31:'UnconfirmedTextMessage',
        32:'TimeSynchronization',
        33:'Who_Has',
        34:'Who_Is',
        35:'ReadRange',
        36:'UtcTimeSynchronization',
        37:'LifeSafetyOperation',
        38:'SubscribeCOVProperty',
        39:'GetEventInformation',
        }
class BACnetResultsFlags(_bit_string):
    _bit_string_map={
        0:'firstitem',
        1:'lastitem',
        2:'moreitems',
        }
class BACnetLimitEnable(_bit_string):
    _bit_string_map={
        0:'lowLimitEnable',
        1:'highLimitEnable',
        }
class BACnetLogStatus(_bit_string):
    _bit_string_map={
        0:'log-disabled',
        1:'buffer-purged',
        }
class BACnetObjectTypesSupported(_bit_string):
    _bit_string_map={
        0:'analog_input',
        1:'analog_output',
        2:'analog_value',
        3:'binary_input',
        4:'binary_output',
        5:'binary_value',
        6:'calendar',
        7:'command',
        8:'device',
        9:'event_enrollment',
        10:'file',
        11:'group',
        12:'loop',
        13:'multi_state_input',
        14:'multi_state_output',
        15:'notification_class',
        16:'program',
        17:'schedule',
        18:'averaging',
        19:'multi_state_value',
        20:'trend_log',
        21:'life_safety_point',
        22:'life_safety_zone',
        23:'accumulator', 
        24:'pulse-converter',
        }
class BACnetActionCommand(_sequence):
    def __init__(self, device_identifier=None, object_identifier=None, property_identifier=None,\
                 property_array_index=None, property_value=None, priority=None, post_delay=None, \
                 quit_on_failure=None, write_successful=None, **keywords):
        _sequence.__init__(self, None, **keywords)
        self.device_identifier=device_identifier
        self.object_identifier=object_identifier
        self.property_identifier=property_identifier
        self.property_array_index=property_array_index
        self.property_value=property_value
        self.priority=priority
        self.post_delay=post_delay
        self.quit_on_failure=quit_on_failure
        self.write_successful=write_successful
    def as_tags(self):
        kw={'object_identifier':self.object_identifier.data_object,
            'property_identifier':self.property_identifier.data_object,
            'property_value':self.property_value.as_tags(),
            'quit_on_failure':self.quit_on_failure,
            'write_successful':self.write_successful,
           }
        if not self.device_identifier is None:
            kw['device_identifier']=self.device_identifier.data_object
        if not self.priority is None:
            kw['priority']=self.priority
        if not self.post_delay is None:
            kw['post_delay']=self.post_delay
        return sequence.BACnetActionCommand(**kw).encoding
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['device_identifier'] = self.device_identifier
        d['object_identifier'] = self.object_identifier
        d['property_identifier'] = self.property_identifier
        d['property_array_index'] = self.property_array_index
        d['property_value'] = self.property_value
        d['priority'] = self.priority
        d['post_delay'] = self.post_delay
        d['quit_on_failure'] = self.quit_on_failure
        d['write_successful'] = self.write_successful
        return d

class BACnetAddressBinding(_sequence):
    can_decode_from_list = 1 
    def __init__(self, device_object_identifier=None, network_number=None, mac_address=None, **keywords):
        _sequence.__init__(self, None, **keywords)
        self.device_object_identifier = device_object_identifier
        self.device_address = BACnetAddress(network_number, mac_address)
        self.data_object = self
    def as_tags(self):
        #@FIXME: as_tags() untested!
        return sequence.BACnetAddressBinding(\
           self.device_object_identifier.data_object,
           self.device_address.network_number,
           array.array('B',self.device_address.mac_address)).encoding
    def __str__(self):
        return str([self.device_object_identifier.object_type, self.device_object_identifier.instance_number,\
               self.device_address.network_number, self.device_address.mac_address])
    def __repr__(self):
        return str(self)
    def decode_from_tags(self, tags):
        # Create an instance of the ApplicationSequence subclass. Pass the given tags
        # list into the ctor, to cause ApplicationSequence.decode() to decode the tags
        # into new data members (ie device_object_identifier, and device_address) 
        # of the created object:
        self.d = sequence.BACnetAddressBinding(decode=tags)
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        # Use new object's dynamically-created members to initialize our own:
        self.device_object_identifier = seq.device_object_identifier
        self.device_address = BACnetAddress(seq.network_number, seq.mac_address)
        self._value = None # may not be best place for this, but cur _value is invalid once we've read valid tags from port
        self._data_object = seq
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_address_binding_list(_ConstructTag(list_of_tags))
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['device_object_identifier'] = self.device_object_identifier
        d['device_address'] = self.device_address
        return d
class BACnetActionList(_sequence):
    def __init__(self, action_list=None, **keywords):
        if action_list is None:
            action_list=[]
        _sequence.__init__(self, action_list, **keywords)
    def as_tags(self):
        list = []
        for a in self.value:
            list.append(a.as_tags())
        return sequence.BACnetActionList(action=list).encoding
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['device_identifier'] = self.device_identifier
        d['list'] = self.value
        return d
        
class BACnetVTSession(_data):
    pass
class BACnetAddress(_sequence):
    """
    Represents a network ID number and a mac address for a bacnet device.
    Can be instantiated by passing an int for the network number, a
    byte array, list or string for the mac_address OR by python tuple
    like (network_id_int, [byte_array_list_or_string]) OR a string that
    will eval() to the tuple.
    Can be accessed with .value or .network_number or .mac_address from the
    north side
    """
    def __init__(self, network_number=None, mac_address=None, **keywords):
        _data.__init__(self, None, **keywords)
        if mac_address is None:
            mac_address = []
            if isinstance(network_number, basestring): #convert from string
                network_number = eval(network_number)
            if isinstance(network_number, tuple):
                mac_address = network_number[1]
                if isinstance(mac_address, basestring):
                    mac_address = array.array('B',mac_address)
                mac_address = list(mac_address)
                network_number = int(network_number[0])
                self._value = (network_number, mac_address)
            elif network_number is not None: #no good
                raise EInvalidValue('BACnetAddress initializer bad format: ' +
                    str(network_number))
        else:
            if isinstance(mac_address, basestring):
                mac_address = array.array('B',mac_address)
            mac_address = list(mac_address)
            self._value = (int(network_number), mac_address)
    def sequence(self):
        return sequence.BACnetAddress(\
           self.network_number,
           array.array('B', self.mac_address))
    def as_tags(self):
        return self.sequence().encoding
    def value_from_data_object(self):
        self._value = (self._data_object.network_number, 
                       list(array.array('B', self._data_object.mac_address)))
    def data_object_from_value(self):
        self._data_object = self.sequence()
    def __getattr__(self, attribute):
        if attribute == 'network_number':
            return self.value[0]
        if attribute == 'mac_address':
            return self.value[1]
        return _sequence.__getattr__(self, attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'network_number':
            self._value = (value, self._value[1])
            self._data_object = None #trigger rebuild
            return
        if attribute == 'mac_address':
            if isinstance(value, basestring):
                value = array.array('B',value)
            value = list(value)
            self._value = (self._value[0], value)
            self._data_object = None
            return
        if attribute == 'value':
            self._value = value
            self._data_object = None
            return
        if attribute == 'data_object':
            self._data_object = value
            self._value = None
            return
        _sequence.__setattr__(self, attribute, value)
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['network_number'] = self.network_number
        d['mac_address'] = self.mac_address
        return d
    def __str__(self):
        return str(self.value)
        
class BACnetLimitEnable(_data):
    pass
class BACnetEventParameters(_data):
    pass
class BACnetRecipient(_data):
    pass
class BACnetDestination(_data):
    pass
class BACnetSetpointReference(_data):
    pass
class BACnetReadAccessSpecification(_data):
    pass
class BACnetReadAccessResult(_data):
    pass
class BACnetSessionKey(_data):
    pass
class BACnetPriorityArray(_data):
    pass
class BACnetARRAY(_data):
    pass
class BACnetUnsigned(_unsigned):
    pass
class BACnetInteger(_data):
    def as_tags(self):
        return (tag.SignedInteger(self.data_object),)
class BACnetBoolean(_enum):
    def as_tags(self):
        return (tag.Boolean(self.data_object),)
class BACnetReal(_data):
    def as_tags(self):
        d = self.data_object
        if d is None:
            if debug: print 'Real type as_tags returning null tag'
            return [tag.Null()] #an empty list to clear an override
        return (tag.Real(float(d)),) #make sure any strings are converted to float
class BACnetClientCOV(_data):
    pass
class BACnetTimeStamp(_data):
    pass
class BACnetLogRecord(_data):
    pass
class BACnetDeviceObjectPropertyReference(_sequence):
    # (device instance number or None, object type, object instance, 
    #  property id, index or None or not present)
    can_decode_from_list = 1 
    def __init__(self, device_instance=None, object_type=None, object_instance=None, property_identifier=None, property_index=None, **keywords):
        if keywords.has_key('decode'):
            _sequence.__init__(self, None, **keywords)
            return
        self._value = None
        self._data_object = None
        if type(device_instance) == types.StringType: #may be string of instance number or tupleType from nodebrowser
            device_instance = eval(device_instance)
        if isinstance(device_instance, BACnetDeviceObjectPropertyReference): #duplicate same type object
            self._data_object = device_instance.data_object
        elif isinstance(device_instance, sequence.BACnetDeviceObjectPropertyReference):
            self._data_object = device_instance
        elif (type(device_instance) == types.TupleType) or (type(device_instance) == types.ListType):
            self._value = device_instance
        elif (type(device_instance) == types.DictType):
            #handles objects preconfigured in broadway.xml
            self._value = [eval(device_instance['device']),
                           eval(device_instance['type']),
                           eval(device_instance['instance']),
                           eval(device_instance['property']),
                           ]
            if device_instance.has_key('index'):
                self._value += [eval(device_instance['index'])]
            else:
                self._value += [None]
        else: #put together from individual pieces
            if isinstance(device_instance, BACnetObjectIdentifier):
                device_instance = device_instance.instance_number
            if isinstance(object_type, BACnetObjectIdentifier):
                object_instance = object_type.instance_number
                object_type = object_type.object_type
            elif object_type is not None: #not none
                object_type = int(object_type) #converts strings or BO type enum
            if object_instance is not None: #if present in command line or already gotten from boid above
                object_instance = int(object_instance)
            if property_identifier is not None:
                property_identifier = int(property_identifier) #converts BPID or string
            self._value = [device_instance, object_type, object_instance, property_identifier]
            if property_index is not None:
                self._value += [int(property_index)]
            else:
                self._value += [None]
        #either self._datatobject or self._value has been set
    def value_from_data_object(self):
        device = self._data_object.device_identifier
        if device == OPTIONAL:
            device = None
        else:
            device = device.instance_number
        pidx = self._data_object.property_index
        if pidx == OPTIONAL:
            pidx = None
        else:
            pidx = int(pidx)
        self._value = [device, 
                       self._data_object.object_identifier.object_type, 
                       self._data_object.object_identifier.instance_number, 
                       int(self._data_object.property_identifier),
                       pidx]
    def data_object_from_value(self):
        keywords = {'object_identifier':BACnetObjectIdentifier(self._value[1], self._value[2]).data_object,
            'property_identifier':self._value[3]}
        if self._value[0] is not None:
            keywords['device_identifier'] = BACnetObjectIdentifier(8, self._value[0]).data_object
        if len(self._value) > 3 and self._value[4] is not None:
            keywords['property_index'] = self._value[4]
        self._data_object = sequence.BACnetDeviceObjectPropertyReference(**keywords)
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_object_property_reference_list(_ConstructTag(list_of_tags))
    def __getattr__(self, attribute):
        if attribute == 'object_identifier':
            return BACnetObjectIdentifier(self.value[1], self.value[2])
        if attribute == 'device_identifier':
            return BACnetObjectIdentifier(8, self.value[0])
        if attribute == 'property_index':
            return self.value[4]
        if attribute == 'device_instance':
            return self.value[0]
        if attribute == 'object_type':
            return self.value[1]
        if attribute == 'object_instance':
            return self.value[2]
        if attribute == 'property_identifier':
            return self.value[3]
        return _sequence.__getattr__(self, attribute)
    def __setattr__(self,attribute,value):
        if attribute == 'object_identifier':
            self.value[1] = value.object_type #force any necessary conversion with self.value
            self._value[2] = value.object_instance
            self._data_object = None #force regen of sequence
            return
        if attribute == 'device_identifier':
            if value is None:
                self.value[0] = None
            else:
                self.value[0] = value.object_instance
            self._data_object = None
            return
        if attribute == 'property_index':
            self.value[4] = value #None or int
            self._data_object = None
            return
        if attribute == 'device_instance':
            self.value[0] = int(value)
            self._data_object = None
            return
        if attribute == 'object_type':
            self.value[1] = int(value)
            self._data_object = None
            return
        if attribute == 'object_instance':
            self.value[2] = int(value)
            self._data_object = None
            return
        if attribute == 'property':
            self.value[3] = value
            self._data_object = None
            return
        return _sequence.__setattr__(self, attribute, value)
   
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['object_identifier'] = self.object_identifier
        d['property_identifier'] = self.property_identifier
        d['property_index'] = self.property_index
        d['device_identifier'] = self.device_identifier
        return d
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.value == o.value
        return 0
class BACnetCOVSubscription(_data):
    pass
class BACnetDeviceObjectReference(_sequence):
    pass
class BACnetObjectPropertyReference(_sequence):
    can_decode_from_list = 1 
    def __init__(self, object_identifier=None, property_identifier=None, property_index=None, **keywords):
        _sequence.__init__(self, None, **keywords)
        self.object_identifier=object_identifier
        self.property_identifier=property_identifier
        if type(property_identifier) == 'int':
            self.property_identifier = BACnetPropertyIdentifier(property_identifier)
        self.property_index=property_index
    def as_tags(self):
        if self.property_index is None:
            return (sequence.BACnetObjectPropertyReference(\
               object_identifer=self.object_identifier.data_object,
               property_identifier=self.property_identifier.data_object).encoding)
        return sequence.BACnetObjectPropertyReference(\
           object_identifer=self.object_identifier.data_object,
           property_identifier=self.property_identifier.data_object,
           property_index=self.property_index).encoding
    def decode_from_tags(self, tags):
        self.d = sequence.BACnetObjectPropertyReference(decode=tags) # BACnetPropertyValue is subclass of ContextSequence
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        self.object_identifier = seq.object_identifier
        self.property_identifier = seq.property_identifier
        self.property_index = seq.property_index
        self.data_object = seq
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_object_property_reference_list(_ConstructTag(list_of_tags))
    def value_from_data_object(self):
        self._value = [self.object_identifier, self.property_identifier, self.property_index]
    def data_object_from_value(self):
        self.object_identifier = self._value[0]
        self.property_identifier = self._value[1]
        self.property_index = self._value[2]
    
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['object_identifier'] = self.object_identifier
        d['property_identifier'] = self.property_identifier
        d['property_index'] = self.property_index
        return d
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.value == o.value
        return 0
class BACnetError(_data):
    pass

class WritePropertyRequest(_data):
    pass

# _value format: list [year, month, day, day_of_week]
# _data_object format: a data.Date object
# <members>: dynamically read/written from/to _value
# <tags>: created dynamimcally, using tag.Date
class BACnetDate(_data):
    _has_magnitude_interface = 0
    def __init__(self, value_year=None, month=None, day=None, day_of_week=None, **keywords):
        self._value = (None, None, None) #, None]
        self._data_object = None
        if keywords.has_key('decode'):
            if debug: 
                print '!!! BACnetDate decode from: ', str(keywords['decode']), type(keywords['decode'])
            _data.__init__(self, None, **keywords)
        elif not value_year is None:
            if type(value_year) == types.FloatType: #using python float representation of date
                s_tm = time.localtime(value_year)
                self._value = (s_tm[0], s_tm[1], s_tm[2]) #, s_tm[6]+1)
            elif (type(value_year) == types.TupleType) or (type(value_year) == time.struct_time):
                value_year = list(value_year) # make sure it's mutable for the mods applied below
                if len(value_year) == 4: #then in (year,month,day,day_of_week) format
                    self._value = (None, None, None, None)
                    self._value = value_year[:4] #list
                    return
                if len(value_year) == 3: #convert to 9 element tuple for conversion
                    value_year = list(value_year)
                    value_year.extend([0,0,0,0,0,-1])
                if len(value_year) == 9: #c code time tuple
                    for i in range(3):
                        if value_year[i] is None:
                            self._value = (value_year[0], value_year[1], value_year[2]) #, None]
                            break
                    else:
                        value_year[6] = 0 # nice arbitrary value
                        s_tm = time.localtime(int(time.mktime(value_year))) # make sure day_of_week is right
                        self._value = (s_tm[0], s_tm[1], s_tm[2]) #, s_tm[6]+1)
            elif type(value_year) == types.IntType: #individual integers
                self._value = (value_year, month, day, day_of_week)
            elif isinstance(value_year, basestring):
                m,d,y = [int(s) for s in value_year.split('/')]
                self._value = (y, m, d)
            else:
                raise EInvalidValue('BACnetDate.__init__() takes Float, 9-Tuple of Ints, time.struct_time, or individual Ints', \
                                    type(value_year))
        #self._has_magnitude_interface = 0
    def as_tags(self):
        return [tag.Date(self.data_object),]
    def value_from_data_object(self):
        _do = self._data_object
        self._value = (_do.year, _do.month, _do.day) #, None) #, _do.day_of_week)
    def data_object_from_value(self):
        if self._value is None:
            self._data_object = data.Date()
            return
        if len(self._value) == 3:
            self._data_object = data.Date(self._value[0],self._value[1],self._value[2])#,self._value[3])
        else:
            self._data_object = data.Date(self._value[0],self._value[1],self._value[2],self._value[3])
#    def __str__(self):
#        return '(%s, %s, %s)' % (str(self.year), str(self.month), str(self.day))
    def __getattr__(self, attribute):
        if attribute == 'year':
            return self.value[0]
        if attribute == 'month':
            return self.value[1]
        if attribute == 'day':
            return self.value[2]
#        if attribute == 'day_of_week':
#            return self.value[3]
        return _data.__getattr__(self, attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'year':
            v = list(self.value)
            v[0] = value
            self._value = tuple(v)
            self._data_object = None
            return
        if attribute == 'month':
            v = list(self.value)
            v[1] = value
            self._value = tuple(v)
            self._data_object = None
            return 
        if attribute == 'day':
            v = list(self.value)
            v[2] = value
            self._value = tuple(v)
            self._data_object = None
            return 
#        if attribute == 'day_of_week':
#            v = list(self.value)
#            v[3] = value
#            self._value = tuple(v)
#            self._data_object = None
#            return 
        _data.__setattr__(self, attribute, value)
    def __cmp__(self, o):
        if isinstance(o,self.__class__):
            #compare the indivdual elements of the date tuple
            #None's match anything as ==
            for i in range(3): #only consider year, month, day.  Not DOW.
                if (self.value[i] is not None) and (o.value[i] is not None):
                    c = cmp(self.value[i], o.value[i])
                    if c != 0: #we have a definitive comparison
                        return c
                    #we still don't know, go to the next element
                #a None is considered equal to anything so go to next element
            return 0 #equal
        raise ENotImplemented
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.__cmp__(o) == 0
        return False
    
# Accept time as another BACnetTime object, float value in epoch seconds
# string hh:mm:ss or separate values
    def get_summary_string(self): # return string representation for scheduler
        # accessing attributes year, month & day will force any needed conversion
        # accessing them after as elements in self._value will save time
        if self.year is None: year = '*'
        else: year = '%04u' % self._value[0]
        if self.month is None: month = '*'
        else: month = '%02u' % self._value[1]
        if self.day is None: day = '*'
        else: day = '%02u' % self._value[2]
        return '%s/%s/%s' % (year, month, day)

class BACnetTime(_data):
    _has_magnitude_interface = 0
    def __init__(self, hour=None, minute=None, second=None, hundredths=None, **keywords):
        self._value = None
        self._data_object = None
        if keywords.has_key('decode'):
            if debug: print '!!! BACnetTime decode from: ', keywords['decode'][0].value
            _data.__init__(self, **keywords)
        else:
            if type(hour) == types.StringType:#convert string hh:mm:ss:hs to list
                s = hour.split(':')
                hour = [int(x) for x in s]
            if isinstance(hour, BACnetTime):
                self._data_object = hour.data_object
            elif (type(hour) == types.TupleType) or (type(hour) == types.ListType):
                if len(hour) == 4: #hmsh
                    self._value = list(hour)
                elif len(hour) == 3: #hms
                    self._value = list(hour) + [0]
                elif len(hour) == 2: #hms
                    self._value = list(hour) + [0,0]
                else:
                    raise EInvalidValue('hour', hour, 'wrong length tuple for BACnetTime')
            elif (type(hour) == types.FloatType): #linux time value
                self._value = list(time.localtime(hour)[3:6]) + [0]
            else:
                if hundredths is None:
                    if type(second) == float:
                        if int(second) != second: #then fraction
                            hundredths = int((second - int(second)) * 100)
                        second = int(second)
                self._value = [hour, minute, second, hundredths]
    def value_from_data_object(self):
        _do = self._data_object
        self._value = [_do.hour, _do.minute, _do.second, _do.hundredths]
    def data_object_from_value(self):
        self._data_object = data.Time(self._value[0],self._value[1],self._value[2],self._value[3])
    def as_tags(self):
        return (tag.Time(self.data_object),)
    def __getattr__(self, attribute):
        if attribute == 'hour':
            return self.value[0]
        if attribute == 'minute':
            return self.value[1]
        if attribute == 'second':
            return self.value[2]
        if attribute == 'hundredths':
            return self.value[3]
        return _data.__getattr__(self, attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'hour':
            self.value[0] = value
            self._data_object = None
            return
        if attribute == 'minute':
            self.value[1] = value
            self._data_object = None
            return 
        if attribute == 'second':
            self.value[2] = value
            self._data_object = None
            return 
        if attribute == 'hundredths':
            self.value[3] = value
            self._data_object = None
            return 
        _data.__setattr__(self, attribute, value)
    def __str__(self):
        hour = str(self.hour)  #in case any of these are None
        minute = str(self.minute)
        second = str(self.second)
        hundredths = str(self.hundredths)
        if not self.hour is None:
            hour = '%02u' % (self.hour)
        if not self.minute is None:
            minute = '%02u' % (self.minute)
        if not self.second is None:
            second = '%02u' % (self.second)
        if self.hundredths: #don't add hundreths if None or zero
            hundredths = '%02u' % (self.hundredths)
            return '%s:%s:%s.%s' % (hour,minute,second,hundredths)
        else:
            return '%s:%s:%s' % (hour,minute,second)

# [[(2003, 8, 27), (2003, 8, 27)]]
def _time_only(attr_strs):
    return  '%s:%s:%s.%s' % (attr_strs[3], attr_strs[4], attr_strs[5],
                             attr_strs[6])
def _time_only_no_hundredths(attr_strs):
    results = '%s:%s:%s' % (attr_strs[3], attr_strs[4], attr_strs[5])
    return  results
def _time_only_no_sec(attr_strs):
    return  '%s:%s' % (attr_strs[3], attr_strs[4])
def _date_only(attr_strs):
    return  '%s/%s/%s' % (attr_strs[1], attr_strs[2], attr_strs[0])
def _date_only_no_year(attr_strs):
    return  '%s/%s' % (attr_strs[1], attr_strs[2])
def _date_only_no_day(attr_strs):
    return  '%s/%s' % (attr_strs[1], attr_strs[0])
_pattern_dict = {
    'xxxiiii':_time_only,
    'xxxiiix':_time_only_no_hundredths,
    'xxxiixx':_time_only_no_sec,
    'iiixxxx':_date_only,
    'xiixxxx':_date_only_no_year,
    'iixxxxx':_date_only_no_day,
    }

class BACnetDateTime(_sequence):
    can_decode_from_list = 1 
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None, hundredths=None, **keywords):
        self.attrs = [year, month, day, hour, minute, second, hundredths]
        _sequence.__init__(self, None, **keywords)
    def value_from_data_object(self):
        self._value = self
    def year(self):
        return self.attrs[0]
    def month(self):
        return self.attrs[1]
    def day(self):
        return self.attrs[2]
    def hour(self):
        return self.attrs[3]
    def minute(self):
        return self.attrs[4]
    def second(self):
        return self.attrs[5]
    def hundredths(self):
        return self.attrs[6]
    def decode_from_tags(self, tags):
        # Create an instance of the ApplicationSequence subclass. Pass the
        # given tags list into the ctor, to cause ApplicationSequence.decode()
        # to decode the tags into new data members of the created object:
        d = sequence.BACnetDateTime(decode=tags)
        # Use new object's dynamically-created Time and Date attributes to
        # initialize our own attributes:
        self.attrs = [d.date.year, d.date.month, d.date.day,
                      d.time.hour, d.time.minute, d.time.second,
                      d.time.hundredths]
    def decode_from_sequence(self, seq):
        self.attrs=[seq.date.year, seq.date.month, seq.date.day,
                    seq.time.hour, seq.time.minute, seq.time.second,
                    seq.time.hundredths]
        self._data_object = seq
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_date_time_list(
            _ConstructTag(list_of_tags)
            )
    def as_tags(self):
        return sequence.BACnetDateTime(
            data.Date(self.year(), self.month(), self.day()),
            data.Time(self.hour(), self.minute(), self.second(),
                      self.hundredths())).encoding
    def __str__(self):
        attr_strs = []
        attr_pattern = ''
        for attr in self.attrs:
            if isinstance(attr, int):
                attr_strs.append('%02u' % attr)
                attr_pattern += 'i'
            else:
                attr_strs.append('XX')
                attr_pattern += 'x'
        if _pattern_dict.has_key(attr_pattern):
            return _pattern_dict[attr_pattern](attr_strs)
        if self.attrs[6] is None:
            return '%s/%s/%s, %s:%s:%s' % (
                attr_strs[1], attr_strs[2], attr_strs[0],
                attr_strs[3], attr_strs[4], attr_strs[5]
                )
        return '%s/%s/%s, %s:%s:%s.%s' % (
                attr_strs[1], attr_strs[2], attr_strs[0],
                attr_strs[3], attr_strs[4], attr_strs[5],
                attr_strs[6]
                )
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['year'] = self.year()
        d['month'] = self.month()
        d['day'] = self.day()
        d['hour'] = self.hour()
        d['minute'] = self.minute()
        d['second'] = self.second()
        d['hundredths'] = self.hundredths()
        return d
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.as_dict() == o.as_dict()
        return 0
#@FIXME: Add methods to convert to/from mpx.lib.datetime objects.
# Do comparisons in those objects.
# Accepts initializing data in these forms:
# (1) Pair of BACnetDate refs
# (2) Pair of data.Date refs
# (3) List or 2tuple containing two lists or 3tuples (year,month,day) (as start_date, with end_date == None)
# (4) Stringized version of (3) (as start_date, with end_date == None)
class BACnetDateRange(_sequence):
    can_decode_from_list = 1 
    def __init__(self, start_date=None, end_date=None, **keywords):
        #self._has_magnitude_interface = 0
        self._data_object=self
        self._value = None
        self._init_mems(start_date, end_date)
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif keywords.has_key('from_seq'):
            self.decode_from_sequence(keywords['from_seq'])
    def _init_mems(self, start_date, end_date):
        self.start_date = BACnetDate()
        self.end_date = BACnetDate()
        if isinstance(start_date, BACnetDate):
            self.start_date = start_date
        elif hasattr(start_date, 'year'): #@FIXME: bring C-code Python objects into the world of 2.1.x+, to support actual typing
            self.start_date.data_object = start_date
        elif type(start_date) == types.StringType:
            start_date = eval(start_date) # result is a tuple containing two 3tuples
        if (type(start_date) == types.TupleType) or (type(start_date) == types.ListType):
            if type(start_date[0]) == types.IntType: #if seperate tuples for start and end
                self.start_date = BACnetDate(start_date) #pass the tuple to convert to date
            else: #if dual tuple for both start and end
                assert end_date == None, 'BACnetDateRange tuple init error'
                assert len(start_date) == 2, 'Wrong tuple length for BACnetDateRange'
                self.start_date = BACnetDate(start_date[0])
                self.end_date = BACnetDate(start_date[1])
                return
        if isinstance(end_date, BACnetDate):
            self.end_date = end_date
        elif hasattr(end_date, 'year'): #@FIXME: bring C-code Python objects into the world of 2.1.x+, to support actual typing
            self.end_date.data_object = end_date
        elif (type(end_date) == types.TupleType) or (type(end_date) == types.ListType):
            self.end_date = BACnetDate(end_date) #pass the tuple to convert to date
    def value_from_data_object(self):
        s = self.start_date
        e = self.end_date
        self._value = ((s.year, s.month, s.day), (e.year, e.month, e.day))
    def data_object_from_value(self):
        self.start_date.year = self._value[0][0]
        self.start_date.month = self._value[0][1]
        self.start_date.day = self._value[0][2]
        self.end_date.year = self._value[1][0]
        self.end_date.month = self._value[1][1]
        self.end_date.day = self._value[1][2]
        self._data_object = self.as_sequence()
    def decode_from_tags(self, tags):
        self.d = sequence.context_decode_bacnet_date_range(_ListAsTags(tags))  #may need to be wrapped with .value
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        #self._init_mems(seq.start_date, seq.end_date) #now done in __setattr__
        self.data_object = seq
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_bacnet_date_range_list(_ConstructTag(list_of_tags))
    def as_sequence(self):
        return sequence.BACnetDateRange(\
           self.start_date.data_object, \
           self.end_date.data_object)
    def as_tags(self):
        return self.as_sequence().encoding                                       
    def __setattr__(self, attribute, value):
        if attribute == 'start_date':
            self.__dict__['start_date'] = value
            self._data_object = None
            self._value = None
            return
        if attribute == 'end_date':
            self.__dict__['end_date'] = value
            self._data_object = None
            self._value = None
            return
        if attribute == 'data_object':
            self._init_mems(value.start_date, value.end_date)
            self._data_object = value
            self._value = None
            return
        _sequence.__setattr__(self, attribute, value)
    def as_dict(self):
        x = self.data_object
        d = _sequence.as_dict(self)
        d['start_date'] = self.start_date
        d['end_date'] = self.end_date
        return d
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.value == o.value
        return 0
    def includes(self, date): #true if date within range, inclusive
        #date must be a BACnetDate object
        return (date >= self.start_date) and (date <= self.end_date)
    def get_summary_string(self):
        x = self.data_object # lazily force conversion if not already done
        return (self.start_date.get_summary_string(), self.end_date.get_summary_string())
class BACnetWeekNDay(BACnetOctetString):
    # BACnetWeekNDay ::= OCTET STRING (SIZE (3)) 
    #-- first octet month (1..14)            1 =January 
    #--      13 = odd months 
    #--      14 = even months 
    #--      X'FF' = any month   ( we use * in text, None in tuple )
    #-- second octet weekOfMonth where: 1 = days numbered 1-7 
    #--     2 = days numbered 8-14 
    #--     3 = days numbered 15-21 
    #--     4 = days numbered 22-28 
    #--     5 = days numbered 29-31 
    #--     6 = last 7 days of this month 
    #--     X'FF' = any week of this month   ( we use * in text, 0 in tuple (None means the entry is not WeekNDay) )
    #-- third octet dayOfWeek (1..7) where 1 = Monday  (we use four element)
    #--      7 = Sunday 
    #--      X'FF' = any day of week  ( we use * in text, None in tuple )
    def __init__(self, value=None):
        # accepts either Octet Striing of 3 bytes in bacnet format
        # or a string with month/dayOfWeek/year/weekOfMonth
        # a tuple (year, month, dayOfMonth, weekOfMonth)
        if value:
            if len(value) > 3: #then in our scheduler string format m/dow/y/wom
                if type(value) == types.TupleType: # (year, month, dow, wom) format 
                    y, m, dow, wom = value[:4]
                    if m is None: m = 255
                    if dow is None: dow = 255
                    if wom is None: wom = 255
                else:
                    m, dow, y, wom = split(value,'/') # if not in proper format then error
                    if m == '*': m = 255
                    if dow == '*': dow = 255
                    if wom == '*': wom = 255
                if int(wom) == 0: wom = 255
                value = ''.join([chr(int(x)) for x in [m, wom, dow]])
        BACnetOctetString.__init__(self, value)
    def get_summary_string(self):
        wnd = self.value
        month, weekOfMonth, dayOfWeek = [ord(b) for b in self.value]
        if month > 14: month = '*'
        if weekOfMonth > 6: weekOfMonth = '*' # means any week
        if dayOfWeek > 7: dayOfWeek = '*' 
        return '%s/%s/*/%s' % (month, dayOfWeek, weekOfMonth)        
    def __str__(self): # for node browser
        wnd = self.value
        month, weekOfMonth, dayOfWeek = [ord(b) for b in self.value]
        if month > 14: month = None
        if weekOfMonth > 6: weekOfMonth = None # means any week
        if dayOfWeek > 7: dayOfWeek = None 
        return '(None,%s,%s,%s)' % (month, dayOfWeek, weekOfMonth)        
    def __repr__(self):
        return repr(self.value)
class BACnetCalendarEntry(_choice):
    can_decode_from_list = 1 
    choice_classes = {
        'date'      :BACnetDate,      #float or string ##/##/## or (y,m,d)
        'date_range':BACnetDateRange, #[(y,m,d),(y,m,d)]
        'week_n_day':BACnetWeekNDay   #'\x00\x00\x00'
        }
    def __init__(self, choice_value=None, choice_name=None, **keywords):
        _choice.__init__(self, choice_value, choice_name, **keywords)
        if self.choice_name is None: #try to guess what class it is from the data type
            if choice_value is not None:
                if type(choice_value) == types.StringType: 
                    if len(choice_value) == 3: #week_n_day
                        self.choice_name = 'week_n_day'
                        return
                    #convert string to tuple(s)
                    choice_value = eval(choice_value)
                if (type(choice_value) == types.TupleType) or (type(choice_value) == types.ListType):
                    if (type(choice_value[0]) == types.TupleType): #date range if tuple of tuples
                        self.choice_name = 'date_range'
                        return
                    if len(choice_value) > 4: # week_n_day?
                        self.choice_name = 'week_n_day'
                        return
                self.choice_name = 'date'
    def value_from_data_object(self):
        seq = getattr(self._data_object,self.choice_name)
        if debug: 
            print '!!! BACnetCalendarEntry value_from_data_object: ', self.choice_name, repr(self._data_object), repr(seq), str(seq), type(seq)
        dt = self.choice_classes[self.choice_name]()
        #print "BACnetCalendarEntry value_from_data_object: ", repr(dt)
        dt.data_object = seq
        self._value = dt.value #
        #print str(self._value), repr(self._value)
    def data_object_from_value(self):
        if debug:
            print 'BACnetCalendarEntry data_object_from_value: ', self.choice_name, repr(self._value)
        dt = self.choice_classes[self.choice_name](self._value)
        kw = {self.choice_name:dt.data_object}
        self._data_object = sequence.BACnetCalendarEntry(**kw)
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_calendar_entry_list(_ConstructTag(list_of_tags))
    def __str__(self): # used by node browser
        dt = self.choice_classes[self.choice_name](self.value)
        return str(dt)
    def get_summary_string(self): #for supporting Scheduler summary string
        dt = self.choice_classes[self.choice_name](self.value) #use this for date and date_range too?
        if self.choice_name == 'date_range':
            return dt.get_summary_string()   # already a tuple of two strings
        # if self.choice_name == 'date': #BACnetDate choice
        # if self.choice_name == 'week_n_day':
        return (dt.get_summary_string(), '') # make same as date range summary

class BACnetSpecialEvent(_choice):
    can_decode_from_list = 1 
    def __init__(self, time_values=None, event_priority=None, period=None, **keywords):
        if keywords.has_key('decode'):
            _choice.__init__(self, None, **keywords)
            return
        self._value = None
        self._data_object = None
        #period can be either string or BACnetCalendarEntry object or None
        if type(time_values) == types.StringType: #from nodebrowser string
            # ([('12:34:56', 73.300003051757812),('11:22:33', 74.5)],16,(2008, 8, 20))
            # ([('12:34:56', 73.300003051757812),('11:22:33', 74.5)],16,(None, 2, 1, 3 )) president's day
            time_values = eval(time_values) 
        if type(time_values) == tuple: #not list
            se = time_values
            time_values = [BACnetTimeValue(tv, **keywords) for tv in se[0]] #convert to list of time value objects
            event_priority = int(se[1])
            period = se[2]
            if type(period) == long: #BOID, not calendary entry
                period = BACnetObjectIdentifier(period)
            else:
                period = BACnetCalendarEntry(period)
        if time_values is not None and event_priority is not None and period is not None:
            self._value = (time_values, event_priority, period)
    def value_from_data_object(self):
        time_values = [BACnetTimeValue(decode=tv) for tv in self._data_object.time_values]
        event_priority = BACnetUnsigned(self._data_object.event_priority) #simple type comes through decoded from seq
        if self._data_object.calendar_entry == sequence.CHOICE: #must be boid instead
            period = BACnetObjectIdentifier(
                self._data_object.calendar_reference.object_type,
                self._data_object.calendar_reference.instance_number)
        else: #since calendar entry
            period = BACnetCalendarEntry(decode=self._data_object.calendar_entry)
        self._value = (time_values, event_priority, period)
    def data_object_from_value(self):
        kw = {'event_priority':BACnetUnsigned(self.value[1]).data_object,
              'time_values':[tv.data_object for tv in self.value[0]]
             }
        if isinstance(self._value[2],BACnetCalendarEntry):
            kw['calendar_entry'] = self._value[2].data_object
        else: #boid
            kw['calendar_reference']=self._value[2].data_object
        self._data_object = sequence.BACnetSpecialEvent(**kw)
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_special_event_list(_ConstructTag(list_of_tags))
    def __getattr__(self, attribute):
        if attribute == 'time_values':
            answer = self.value[0]
            self._data_object = None
            return answer
        if attribute == 'event_priority':
            answer = self.value[1]
            self._data_object = None
            return answer
        if attribute == 'period':
            answer = self.value[2]
            self._data_object = None
            return answer
        return _sequence.__getattr__(self, attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'time_values':
            self.value[0] = value
            return 
        if attribute == 'event_priority':
            self.value[1] = value
            return 
        if attribute == 'period':
            self.value[2] = value
            return 
        _sequence.__setattr__(self, attribute, value)
    def __str__(self): #answer the string representation of this object
        answer = '(['
        for tv in self.time_values:
            answer += str(tv) + ','
        answer += '],' + str(self.event_priority) + ',' + str(self.period) + ')'
        return answer
    def get_summary(self): # to support Scheduler functions to make this equiv to a scheduler.Daily.  List of BACnetTimeValue get_summary.
        answer = []
        index = 1
        for v in self.value[0]: #BACnetTimeValues portion of value
            vsum = v.get_summary()
            vsum.insert(0,'entry_'+str(index)) #give it a simple name
            answer.append(vsum)
            index += 1
        return answer
            

#BACnetTime object paired with a simple value
#Time element can be entered as in BACnetTime object above
#Value element can be any simple numeric or enum type
class BACnetTimeValue(_sequence):
    def __init__(self, time=None, value=None, **keywords):
        self._value = None
        self._data_object = None
        if keywords.has_key('decode'):
            #if debug: print '!!! BACnetTimeValue decode from: ', keywords['decode'][0].value
            _sequence.__init__(self, **keywords)
        elif isinstance(time, sequence.BACnetTimeValue): #being inialized with sequence
            self.decode_from_sequence(time)
            return
        elif type(time) == types.StringType:#convert string hh:mm:ss:hs valueto list
            time = eval(time) #tuple with time string and Value
        conversion = keywords.get('time_value_abstract_type', float)
        if type(time) == tuple or type(time) == list:
            if conversion == types.BooleanType:
                time[1] = int(time[1])
            #print 'BACnetTimeValue init: ', time
            self._value = [BACnetTime(time[0]), conversion(time[1])] #@TODO Is this a Vendor specific issue? KMC will not accept INT datatype while spec allows it
            if debug: print 'BACnetTimeValue init value ', str(self._value)
        elif time is not None and value is not None:
            self._value = [BACnetTime(time), conversion(value)]
    def value_from_data_object(self):
        _do = self._data_object #sequence of Time and Value
        self._value = [BACnetTime([_do.time.hour,_do.time.minute,_do.time.second,_do.time.hundredths]), _do.value]
    def data_object_from_value(self):
        self._data_object = sequence.BACnetTimeValue(self._value[0].data_object, self._value[1])
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_bacnet_time_value_list(_ConstructTag(list_of_tags))
    def decode_from_tags(self, tags):
        self.d = sequence.BACnetTimeValue(decode=tags)
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        self.data_object = seq
    def as_tags(self):
        return self.data_object.encoding
    def __getattr__(self, attribute):
        if attribute == 'time':
            answer = self.value[0]
            self._data_object = None #since time may be assigned to, force rebuild of seq
            return answer
        if attribute == 'hour':
            return self.value[0].hour
        if attribute == 'minute':
            return self.value[0].minute
        if attribute == 'second':
            return self.value[0].second
        if attribute == 'hundredths':
            return self.value[0].hundredths
        if attribute == 'Value':
            return self.value[1]
        return _sequence.__getattr__(self, attribute)
    def __setattr__(self, attribute, value):
        if attribute == 'hour':
            self.time.hour = value
            return
        if attribute == 'minute':
            self.time.minute = value
            return 
        if attribute == 'second':
            self.time.second = value
            return 
        if attribute == 'hundredths':
            self.time.hundredths = value
            return 
        if attribute == 'Value':
            self._value[1] = value
            self._data_object = None
            return 
        _sequence.__setattr__(self, attribute, value)
    def __str__(self):
        answer = str(self.time)
        return str((answer, self.Value,)) #"('12:34:56',72.1)" 
    def get_summary(self): #to support Scheduler functions to make this equiv to a scheduler.DailyEntry.  List of two strings for hms & value
        return [str(self.value[0]), ('%.3f' % (self.value[1],)).rstrip('0').rstrip('.')]
class BACnetDailySchedule(_sequence): #a list of TimeValue objects
    can_decode_from_list = 1 
    def __init__(self, time_values=None, **keywords):
        self._value = None
        self._data_object = None
        if keywords.has_key('decode'):
            _sequence.__init__(self, time_values, **keywords)
        else:
            self._value = [] #if list is present but empty, we need to be not None
            if time_values is None:
                time_values=[]
                self._value = None #if None was passed in, truely be empty
            elif type(time_values) == types.StringType:
                time_values = eval(time_values)
            if time_values:
                if debug: print 'BACnetDailySchedule init: ', str(time_values)
                self._value = [BACnetTimeValue(str(tv), **keywords) for tv in time_values] #list of tv's
                if debug: print 'BACnetDailySchedule init  value ', str(self._value)
    def value_from_data_object(self):
        self._value = [BACnetTimeValue(s) for s in self._data_object.time_values]
    def data_object_from_value(self):
        self._data_object = sequence.BACnetDailySchedule(time_values=[v.data_object for v in self._value])
    def decode_from_tags(self, tags):
        self.d = sequence.BACnetDailySchedule(decode=tags) # BACnetPropertyValue is subclass of ContextSequence
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        self.data_object = seq
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_bacnet_daily_schedule_list(_ConstructTag(list_of_tags))
    def as_tags(self):
        return self.data_object.encoding
    def as_dict(self):
        d = _sequence.as_dict(self)
        d['time_values'] = self.value
        return d
    def __str__(self):
        answer = '['
        for v in self.value:
            answer += str(v)
            answer += ','
        return answer + ']'
    def get_summary(self): # to support Scheduler functions to make this equiv to a scheduler.Daily.  List of BACnetTimeValue get_summary.
        answer = []
        index = 1
        for v in self.value:
            vsum = v.get_summary()
            vsum.insert(0,str(index))
            answer.append(vsum)
            index += 1
        return answer
class BACnetRecipient(_choice): #a device or object that receives a time sync message
    can_decode_from_list = 1            
    choice_classes = {
        'device'    :BACnetObjectIdentifier,  #Device ID of recipient
        'address'   :BACnetAddress
        }
    def __init__(self, choice_value=None, choice_name=None, **keywords):
        if isinstance(choice_value, basestring):
            choice_value = eval(choice_value)
        if choice_name is None: #need to guess choice
            #if tuple, then choice is address, if int, then device
            if isinstance(choice_value, tuple): #bacnet address (net, addr)
                choice_name = 'address'
            elif isinstance(choice_value, dict): #dictionary 
                choice_name = choice_value['name']
                choice_value = choice_value['value']
            else: #Device ID for anything else
                choice_name = 'device'
        _choice.__init__(self, choice_value, choice_name, **keywords)
    def value_from_data_object(self):
        if self._data_object is None:
            return None
        seq = getattr(self._data_object,self.choice_name)
        if debug: 
            print '!!! BACnetRecipient value_from_data_object: ', \
                self.choice_name, repr(self._data_object), \
                repr(seq), str(seq), type(seq)
        dt = self.choice_classes[self.choice_name]()
        dt.data_object = seq
        self._value = dt.value
        if self.choice_name == 'device': #bacnet object id method
            #we know the object type, just give the instance number
            self._value = dt.instance_number
        #print str(self._value), repr(self._value)
    def data_object_from_value(self):
        if debug:
            print 'BACnetRecipient data_object_from_value: ', \
                self.choice_name, repr(self._value)
        value = self._value
        if self.choice_name == 'device':
            value = 33554432 + value #convert instance number to Device ID
        dt = self.choice_classes[self.choice_name](value)
        kw = {self.choice_name:dt.data_object}
        self._data_object = sequence.BACnetRecipient(**kw)
    def decode_list_of(self, list_of_tags):
        return sequence.context_decode_bacnet_recipient_list(_ConstructTag(list_of_tags))

class BACnetPropertyValue_seq(_sequence):
    _has_magnitude_interface = 0
    def __init__(self, prop_id=None, prop_val=None, priority=None, prop_idx=None, **keywords):
        #self._has_magnitude_interface = 0
        self._data_object=self
        self._value = None
        self._init_mems(prop_id, prop_val, priority, prop_idx)
        if keywords.has_key('decode'):
            self.decode(keywords['decode'])
        elif keywords.has_key('from_seq'):
            self.decode_from_sequence(keywords['from_seq'])
    def _init_mems(self, prop_id, prop_val, priority=None, prop_idx=None):
        self.prop_id = prop_id
        self.prop_val = prop_val
        self.priority = priority
        self.prop_idx = prop_idx
    def value_from_data_object(self):
        self._value = [self.prop_id, self.prop_val, self.prop_idx, self.priority]
    def data_object_from_value(self):
        self.prop_id = self._value[0]
        self.prop_val = self._value[1]
        self.prop_idx = self._value[2]
        self.priority = self._value[3]
    def decode_from_tags(self, tags):
        self.d = BACnetPropertyValue(decode=tags) # BACnetPropertyValue is subclass of ContextSequence
        self.decode_from_sequence(self.d)
    def decode_from_sequence(self, seq):
        self._init_mems(seq.property_identifier, seq.value, seq.property_index, seq.priority)
        self.data_object = seq
    def as_sequence(self):
        return sequence.BACnetPropertyValue(self.prop_id, self.prop_idx, self.prop_val, self.priority)
    def as_tags(self):
        return self.as_sequence().encoding                                       
    def __setattr__(self, attribute, value):
        if attribute == 'prop_id':
            self.__dict__['prop_id'] = value
            self._data_object = None
            self._value = None
            return
        if attribute == 'prop_val':
            self.__dict__['prop_val'] = value
            self._data_object = None
            self._value = None
            return
        if attribute == 'prop_idx':
            self.__dict__['prop_idx'] = value
            self._data_object = None
            self._value = None
            return
        if attribute == 'priority':
            self.__dict__['priority'] = value
            self._data_object = None
            self._value = None
            return
        _sequence.__setattr__(self, attribute, value)
    def as_dict(self):
        x = self.data_object #make sure iv's are up to date
        d = _sequence.as_dict(self)
        d['prop_id'] = self.prop_id
        d['prop_val'] = self.prop_val
        d['prop_idx'] = self.prop_idx
        d['priority'] = self.priority
        return d
    def __eq__(self, o):
        if isinstance(o,self.__class__):
            return self.value == o.value
        return 0
   

class BACnetAbstract(_data):
    def decode_from_tags(self, tags):
        tag = tags[0]
        self._data_object=tag.value
        self._value = None
        try:
            if tag.number == 1: #"Boolean":
                self._data_object = bool(self._data_object)
            elif tag.number == 9: #"Enumerated":
                self._data_object = EnumeratedValue(self._data_object, 
                    str(self._data_object))
        except:
            pass
        return self._data_object

    #depending on data type, produce best guess for the right tag
    def as_tags(self):
        d = self.value
        if type(d) == types.StringType:
            try:
                d = eval(d)
            except: #did not evaluate so just send as string
                return [tag.CharacterString(d)]
        if d is None:
            return [tag.Null()]
        if type(d) == types.IntType:
            if d > 0:
                return [tag.UnsignedInteger(d)]
            return [tag.SignedInteger(d)]
        if type(d) == types.FloatType:
            return [tag.Real(d)]
        #try enumeration
        return [tag.Enumerated(d)]
    

def key_at_value(dict, value):
    for i in dict.keys():
        if dict[i] == value:
            return i
    return None
class _ConstructTag:
    def __init__(self, list_of_tags):
        self.value = list_of_tags

enum_2_class = {
    "PTYPE_BOOLEAN"                   : BACnetBoolean,
    "PTYPE_UNSIGNEDINT"               : BACnetUnsigned,
    "PTYPE_SIGNEDINT"                 : BACnetInteger,
    "PTYPE_REAL"                      : BACnetReal,
    "PTYPE_OCTETSTRING"               : BACnetOctetString,
    "PTYPE_CHARSTRING"                : BACnetCharacterString,
    "PTYPE_BITSTRING"                 : _bit_string,
    "PTYPE_ENUMERATED"                : _enum,
    "PTYPE_DATE"                      : BACnetDate,
    "PTYPE_TIME"                      : BACnetTime,
    "PTYPE_BACNET_OBJECT_ID"          : BACnetObjectIdentifier,
    "PTYPE_BACNET_EVENT_STATE"        : BACnetEventState,
    "PTYPE_BACNET_DATE_TIME"          : BACnetDateTime,
    "PTYPE_BACNET_DATE_RANGE"         : BACnetDateRange,
    "PTYPE_BACNET_OBJ_PROP_REFERENCE" : BACnetObjectPropertyReference,
    "PTYPE_BACNET_SERVICES_SUPPORTED" : BACnetServicesSupported,
    "PTYPE_BACNET_OBJ_TYPES_SUPPORTD" : BACnetObjectTypesSupported,
    "PTYPE_BACNET_STATUS_FLAGS"       : _bit_string,
    "PTYPE_BYTESTRING2"               : _data,
    "PTYPE_APPLICATION_MEMBER"        : _sequence,
    "PTYPE_BACNET_ADDRESS_BINDING"    : BACnetAddressBinding,
    "PTYPE_BACNET_VT_SESSION"         : BACnetVTSession,
    "PTYPE_BACNET_RECIPIENT"          : BACnetRecipient,
    "PTYPE_BACNET_COV_SUBSCRIPTION"   : BACnetCOVSubscription,
    "PTYPE_BACNET_TIME_STAMP"         : BACnetTimeStamp,
    "PTYPE_BACNET_SESSION_KEY"        : BACnetSessionKey,
    "PTYPE_BACNET_DAILY_SCHEDULE"     : BACnetDailySchedule,
    "PTYPE_BACNET_TIME_VALUE"         : BACnetTimeValue,
    "PTYPE_BACNET_SPECIAL_EVENT"      : BACnetSpecialEvent,
    "PTYPE_BACNET_DEV_OBJ_PROP_REFERENCE" : BACnetDeviceObjectPropertyReference,
    "PTYPE_BACNET_CALENDAR_ENTRY"     : BACnetCalendarEntry,
    "PTYPE_ABSTRACT"                  : BACnetAbstract, #means we don't know the data type
    }

