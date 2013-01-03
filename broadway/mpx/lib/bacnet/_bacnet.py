"""
Copyright (C) 2001 2002 2003 2004 2005 2006 2007 2010 2011 Cisco Systems

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
import array
import time
import types
import threading
import copy
from struct import *

from mpx.lib import msglog, debug as lib_debug
from mpx.lib.bacnet import apdu, npdu, network, tag, data
from mpx.lib.bacnet.apdu import BACNET_CONFIRMED_SERVICE_REQUEST_PDU, \
                                BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU, \
                                BACNET_ERROR_PDU, BACNET_REJECT_PDU, \
                                BACNET_ABORT_PDU, APDU
from mpx.lib.bacnet.constants import *
from mpx.lib.bacnet.network import _device_info, _who_are_devices, _device_table
from mpx.lib.bacnet import sequence
from _exceptions import *
from mpx.lib.exceptions import EInvalidValue, EPermission
from mpx.lib.bacnet import EInvalidTrendData
from mpx.lib.node import as_node

from sequence import OPTIONAL

DEBUG = 0
_debug = 0
BACNET_VENDOR_ID_TRANE = 2
BACNET_TRANE_BCU_OBJECT_ID = 8
BACNET_WORKSTATION_DEVICEID_START = 80
BACNET_PROPERTY_IDENTIFIER_OBJECT_NAME = 77
BACNET_PROPERTY_IDENTIFIER_PRESENT_VALUE = 85
BACNET_PROPERTY_IDENTIFIER_PRIORITY_ARRAY = 87
BACNET_OBJECT_TYPE_ANALOG_OUTPUT = 1
BACNET_OBJECT_TYPE_ANALOG_VALUE = 2
BACNET_OBJECT_TYPE_BINARY_OUTPUT = 4
BACNET_OBJECT_TYPE_BINARY_VALUE = 5
BACNET_OBJECT_TYPE_MULTISTATE_OUTPUT = 14
BACNET_OBJECT_TYPE_MULTISTATE_VALUE = 19

from mpx.lib.bacnet.network import BACNET_RPM_UNKNOWN, BACNET_RPM_OK, \
                                   BACNET_RPM_SINGLE_OK, BACNET_RPM_NOT_SUPPORTED

def recv_response(request_id, timeout=3.0):
    r = network.recv_response(request_id, timeout)
    if r.pdu_type == BACNET_ERROR_PDU:
        raise BACnetError(r)
    elif r.pdu_type == BACNET_REJECT_PDU:
        raise BACnetReject(r)
    elif r.pdu_type == BACNET_ABORT_PDU:
        raise BACnetAbort(r)
    return r
def recv_callback_helper(r):
    if r.pdu_type == BACNET_ERROR_PDU:
        raise BACnetError(r)
    elif r.pdu_type == BACNET_REJECT_PDU:
        raise BACnetReject(r)
    elif r.pdu_type == BACNET_ABORT_PDU:
        raise BACnetAbort(r)
    return r
    
def simple_ack_pdu(msg):
    if DEBUG:
        print 'BACNET SERVER: simple ack'
    rp = apdu.BACnetSimpleACK_APDU() #APDU()
    rp.version = 1
    rp.choice = msg.choice
    rp.invoke_id = msg.invoke_id
    if msg.sspec:
        rp.dspec = 1
        rp.dadr = msg.sadr
        rp.dnet = msg.snet
        rp.hop_count = 255
    return rp.as_npdu()

def complex_ack_pdu(msg, response):
    if DEBUG:
        print 'BACNET SERVER: response: ', str(response)
    rp = apdu.BACnetComplexACK_APDU() #APDU()
    rp.choice = msg.choice
    rp.invoke_id = msg.invoke_id
    #@fixme - get routing info
    if msg.sspec:
        if DEBUG: print msg.sadr, msg.snet
        rp.dspec = 1
        rp.dadr = msg.sadr
        rp.dnet = msg.snet
        rp.hop_count = 255
    rp.version = 1
    d = array.array('c')
    for tg in response:
        d.fromstring(tg.encoding)
        if DEBUG: print tg.value
    rp.data = d.tostring()
    if DEBUG:
        print rp
    return rp #.as_npdu()

def error_pdu(msg, error_class, error_code):
    if DEBUG:
        print 'BACNET SERVER: error response: '
    rp = apdu.BACnetErrorAPDU() #APDU()
    rp.version = 1
    rp.choice = msg.choice
    rp.invoke_id = msg.invoke_id
    rp.data.fromstring(tag.Enumerated(error_class).encoding)
    rp.data.fromstring(tag.Enumerated(error_code).encoding)
    if msg.sspec:
        rp.dspec = 1
        rp.dadr = msg.sadr
        rp.dnet = msg.snet
        rp.hop_count = 255
    return rp.as_npdu()
    
#def error_ack_pdu(msg, error_class, error_code):
    
# @fixme Decode the BACnet-SimpleACK-PDU?
def cov_subscription_request(device, prop_tuple, subscription_type, \
               lifetime, subscription_pid, **keywords):
    object = prop_tuple[0]
    instance = prop_tuple[1]

    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 5 # Subscribe COV Request

    rp.data = tag.Context(0,data.\
              encode_unsigned_integer(subscription_pid)).encoding
    objID =   tag.Context(1,data.BACnetObjectIdentifier(object,instance))
    rp.data = rp.data + objID.encoding
    rp.data = rp.data + \
              tag.Context(2,data.\
              encode_boolean(subscription_type)).encoding
    rp.data = rp.data + \
              tag.Context(3,data.\
              encode_unsigned_integer(lifetime)).encoding
    if keywords.has_key('callback'):
        keywords['callback'].callback(_cov_subscription_callback)
        request_id = network.send_request(device, rp, **keywords)
        return keywords['callback']
    else: #block until answer else let tsm handle callback
        request_id = network.send_request(device, rp)
        r = recv_response(request_id)
        return r

def _cov_subscription_callback(tsm):
    try:
        if tsm.exception:
            raise tsm.exception
        r = tsm.response
        recv_callback_helper(r)
        return r
    except Exception, e:
        return e
    except:
        import sys
        return Exception(sys.exc_info()[0])

def cov_notification_msg(server_device, msg, confirmed):
    notif = tag.decode(msg.data)
    if DEBUG: print 'COV NOTIFICATION: ', notif 
    #convert request into a list of cov specifications
    ss = sequence.CovNotification(decode=notif.value)
    if DEBUG: print 'COV NOTIFICATION sequence: ', ss
    pid = ss.pid 
    if DEBUG: print 'COV NOTIFICATION pid: ', pid 
    device_id = ss.device_identifier.instance_number
    if DEBUG: print 'COV NOTIFICATION device_id: ', device_id
    time_remaining = ss.time_remaining 
    if DEBUG: print 'COV NOTIFICATION time_remaining: ', time_remaining 

    if _device_table.has_key(device_id):
        device = _device_table[device_id]
    else:
        # Unknown device.
        return error_pdu(msg, 5, 25)

    try: 
        if device.node is None:
            dnode = as_node('/services/network/BACnet/internetwork/Devices/' + str(device_id))
            device.node = dnode

        o = device.node.as_node((str(ss.object_identifier.object_type)) \
            + '/'+ (str(ss.object_identifier.instance_number)))

    except:
        return error_pdu(msg, 5, 25) 
    if DEBUG: print 'COV NOTIFICATION object: ', o

    for pv in ss.list_of_property_values:
        try:
            p = o.get_child(str(pv.property_identifier), auto_discover=0)
        except ENoSuchName:
            if DEBUG: print 'COV NOTIFICATION ENOSUCHNAME'
            # This can happen if the property we are refering to is
            # not instantiated (because it isn't polled/monitored/not-of-
            # interest. Example: We are only monitoring present-value
            # property, but not status-flags. Ignore for now.

        else:
            p.cov_notif_processing(pv.value, pid, time_remaining)

    return simple_ack_pdu(msg)    


def read_property(device, prop):
    object = prop[0]
    instance = prop[1]
    property = prop[2]
    arrayidx = None
    if len(prop) > 3 :
        arrayidx = prop[3]

    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 12

    objID =   tag.Context(0,data.BACnetObjectIdentifier(object,instance))
    propID =  tag.Context(1,data.encode_enumerated(property))
    rp.data = objID.encoding + propID.encoding
    if arrayidx is not None and arrayidx != -1:
        rp.data = rp.data + \
                  tag.Context(2,data.encode_unsigned_integer(arrayidx)).\
                  encoding
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    response = tag.decode(r.data)
    return response

def read_property_g3(device, prop, timeout=3.0, **keywords):
    object = prop[0]
    instance = prop[1]
    property = prop[2]
    arrayidx = None
    if len(prop) > 3 :
        arrayidx = prop[3]

    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 12

    objID =   tag.Context(0,data.BACnetObjectIdentifier(object,instance))
    propID =  tag.Context(1,data.encode_enumerated(property))
    rp.data = objID.encoding + propID.encoding
    if arrayidx is not None and arrayidx != -1:
        rp.data = rp.data + \
                  tag.Context(2,data.encode_unsigned_integer(arrayidx)).\
                  encoding
    if keywords.has_key('callback'):
        keywords['callback'].callback(_read_property_callback)
        request_id = network.send_request(device, rp, timeout, **keywords)
        return keywords['callback']
    else: #block until answer else let tsm handle callback
        request_id = network.send_request(device, rp, timeout)
        r = recv_response(request_id, timeout)
        response = tag.decode(r.data)
        return sequence.ReadPropertyACK(decode=response.value)

def _read_property_callback(tsm):
    try:
        if tsm.exception:
            raise tsm.exception
        r = tsm.response
        recv_callback_helper(r)
        response = tag.decode(r.data)
        return sequence.ReadPropertyACK(decode=response.value)
    except Exception, e:
        return e
    except:
        import sys
        return Exception(sys.exc_info()[0])

#bacnet plugfest, improved granularity of errorpdu response for problems during requests
def server_read_property(device, msg):
    s = None
    o = None
    ss = None
    p = None
    try:
        #device.time_rp.begin()
        request = tag.decode(msg.data)
        if DEBUG: print 'SERVER READ PROPERTY request: ', request
        s = sequence.ReadPropertyRequest(decode=request.value)
        if DEBUG: print 'SERVER READ PROPERTY sequence: ', s
        o = device.find_bacnet_object(s.object_identifier)
        if o is None: # object not found
            raise ENotFound('BACnet Server Read, Object not found, Type: %d Instance: %d propID: %d' % \
                            (s.object_identifier.object_type, 
                             s.object_identifier.instance_number,
                             s.property_identifier))
        if DEBUG: print 'SERVER READ PROPERTY object: ', o
        ss = s.property_identifier
        if DEBUG: print 'ss = ', ss
        p = o.find_property(ss)
        if o is None: # object not found
            raise ENotFound('BACnet Server Read, Prop not found, Type: %d Instance: %d propID: %d' % \
                            (s.object_identifier.object_type, 
                             s.object_identifier.instance_number,
                             s.property_identifier))
        if DEBUG: print 'SERVER READ PROPERTY property: ', p
        i = None
        answer = sequence.ReadPropertyACK()
        if s.property_array_index != OPTIONAL:
            if DEBUG: print '_bacnet.serverreadproperty ', s.property_array_index
            i = s.property_array_index
            answer.property_array_index = i
            if DEBUG: print i
        answer.object_identifier = s.object_identifier
        answer.property_identifier = s.property_identifier
        answer.property_value = p.as_tags(i)  #this is where we retrieve the value from the node
        answer = complex_ack_pdu(msg, answer.encoding)
        #device.time_rp.end()
        return answer
    except:
        #@fixme use literals not numbers
        msglog.log('mpx:bacnet',msglog.types.ERR,str(msg))
        msglog.exception()
        if p:
            return error_pdu(msg, 2, 25) # operational-problem
        if o:
            return error_pdu(msg, 2, 32) # unknown-property 
        if s:
            return error_pdu(msg, 1, 31) # unknown-object 
        return error_pdu(msg, 2, 0) # other

def server_read_property_multiple(device, msg):
    request = tag.decode(msg.data)
    if DEBUG: print 'SERVER READ PROPERTY MULTIPLE request: ', request
    results = []
    #convert request into a list of read access specifications
    ss = sequence.context_read_access_specification_list(request)
    o = None
    p = None
    if DEBUG: print 'SERVER READ PROPERTY sequence: ', ss
    #device.time_rpm.begin()
    for s in ss:
        o = device.find_bacnet_object(s.object_identifier)
        if DEBUG: print 'SERVER READ PROPERTY object: ', o
        result = sequence.ReadAccessResult()
        result.object_identifier = s.object_identifier
        props = []
        for spec in s.list_of_specs:
            prop_result = sequence._ReadPropertyMultipleResult()
            prop_result.property_identifier = spec.property_identifier
            i = None
            if spec.property_index != OPTIONAL:
                i = spec.property_index
                prop_result.property_array_index = i
            try:
                p = o.find_property(spec.property_identifier)
                prop_result.property_value = p.as_tags(i)
            except:
                if p:
                    prop_result.property_access_error = sequence.Error(2,25) #operational error
                elif o:
                    prop_result.property_access_error = sequence.Error(2,32) #unknown property
                else: #unkown object
                    prop_result.property_access_error = sequence.Error(1,31) #unknown object
                if DEBUG: print 'SERVER property_access_error: ', str(prop_result.property_access_error), \
                      s.object_identifier.object_type,  s.object_identifier.instance_number, \
                      str(spec.property_identifier)
            if DEBUG: print 'SERVER READ PROPERTY property: ', p
            props.append(prop_result.encoding)
        result.list_of_results = props
        results.extend(result.encoding)
    if DEBUG: print 'SERVER READ PROPERTY MULTIPLE request results: ', results
    answer = complex_ack_pdu(msg, results)
    #device.time_rpm.end()
    return answer
    
def _read_property_multiple_g3(device, properties, timeout=3.0, **keywords):
    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 14

    rp.data = array.array('c')
    for prop in properties:
        object = prop[0]
        instance = prop[1]
        property = prop[2]
        objID = tag.Context(0,data.BACnetObjectIdentifier(object,instance))

        if isinstance(property, types.TupleType):
            tags = []
            for pid in property: #loop through list of properties
                if isinstance(pid, types.TupleType): #may have index
                    if len(pid) > 1: #index
                        tags.append(tag.Context(0, data.encode_enumerated(pid[0])))
                        tags.append(tag.Context(1, data.encode_unsigned_integer(pid[1])))
                        continue
                    pid = pid[0] #doen't need to be tuple
                tags.append(tag.Context(0,data.encode_enumerated(pid)))
            propID = tag.Construct(1,tags) #frame it in contruct tags
        else:
            if len(prop) < 4 or prop[3] == -1:
                propID =  tag.Construct(
                    1,[tag.Context(0,data.encode_enumerated(property))]
                    )
            else:
                arrayidx = prop[3]
                propID = tag.Construct(
                    1,[tag.Context(0, data.encode_enumerated(property)),
                       tag.Context(1, data.encode_unsigned_integer(arrayidx))]
                    )
        rp.data.fromstring(objID.encoding)
        rp.data.fromstring(propID.encoding)
    #return rp
    if DEBUG:
        for c in rp.data:
            print hex(ord(c)),'  ',
        print ''
    if keywords.has_key('callback'):
        keywords['callback'].callback(_read_property_multiple_callback)
        network.send_request(device, rp, timeout, **keywords)
        return keywords['callback'] #used as flag
    request_id = network.send_request(device, rp, timeout)
    r = recv_response(request_id, timeout)
    responses = tag.decode(r.data)
    return sequence.context_read_access_result_list(responses)

def _read_property_multiple_callback(tsm):
    try:
        if tsm.exception:
            raise tsm.exception
        r = tsm.response
        recv_callback_helper(r)
        responses = tag.decode(r.data)
        return sequence.context_read_access_result_list(responses)
    except Exception, e:
        return e
    except:
        import sys
        return Exception(sys.exc_info()[0])
    
##
# @return A list of mpx.lib.bacnet.sequence.ReadAccessResult objects
#         representing the values returned from the BACnet
#         ReadPropertyMultiple service.
# @note This function attempts to detect devices with "bad" ReadPropertyMultiple
#       implementations and "falls back" to ReadProperty (the returned list
#       still simulates ReadPropertyMultiple).
# @fixme Catch BACnet exception raised when the target device does not
#        support RPM and fall back to RP.  Note:  Try blocks are
#        expensive, so only set up the try/except when fallback=0 (unknown).
# @param properties is a list that can be in three forms. Form 1 is a list of tuples
#        with each tuple containing the object type, object instance and property
#        ID number, ex: [(type, instance, prop id, optional index),].  The second form replaces
#        property ID with a tuple of ID's: [(type, instance, (prop 1, prop2,)),].
#        The third form replaces the props in form 2 with tuples of prop ID and 
#        index numbers: [(type, instance, ((prop 1, index 1), (prop 1, index 2),)),]
#
def read_property_multiple_g3(device, properties, timeout=3.0, no_fallback=0):
    # Some device's do not properly answer multiple properties to multiple
    # objects. This method first tries RPM, then RPM(singular) and finially RP
    # to retrieve a list of properties.
    # A readPropertyFallback attribute remembers which mode was successful and
    # that is used in subsequent reads.
    if (not (_device_table.has_key(device)) or \
        (_device_table[device].readPropertyFallback < BACNET_RPM_SINGLE_OK)):
        results = _read_property_multiple_g3(device,properties, timeout)
        if (results != None):
            if (len(results) == len(properties)): 
                _device_table[device].readPropertyFallback=1 # No fallback needed.
                return results
            elif no_fallback != 0:
                return results
            else:
                # Broken device?
                _device_table[device].readPropertyFallback=0

    results = []
    properties = copy.copy(properties)
    while properties:
        property = properties.pop(0)
        try:
            rp_result = read_property_g3(device, property)
            if (rp_result is not None): #remember this worked
                if (_device_table[device].readPropertyFallback == BACNET_RPM_UNKNOWN):
                    msglog.log('broadway', msglog.types.WARN,
                               'read_property fallback for device = ' +
                               str(device))
                    _device_table[device].readPropertyFallback = BACNET_RPM_NOT_SUPPORTED
                #convert result to RPM style
                result = sequence.ReadAccessResult()
                result.object_identifier = rp_result.object_identifier
                result.list_of_results = [
                    sequence._ReadPropertyMultipleResult(
                        property_identifier=rp_result.property_identifier,
                        property_array_index=rp_result.property_array_index,
                        property_value=rp_result.property_value)
                    ]
            else:
                # Place holder...
                result = ReadAccessResult()
        except BACnetError, e:
            # Simulate RPMs behaviour when a subset of reads fail.
            error = sequence.Error(decode=tag.decode(e.npdu.data).value)
            result = sequence.ReadAccessResult()
            result.object_identifier = data.BACnetObjectIdentifier(property[0],
                                                                   property[1])
            if len(property) > 3 and property[3] != -1:
                index = property[3]
            else:
                index = -1
            result.list_of_results = [
                sequence._ReadPropertyMultipleResult(
                    property_identifier=property[2],
                    property_array_index=index,
                    property_access_error=error)
                ]
        results.append(result)
    return results

def read_property_multiple_real2(device, properties):
    results = []

    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 14

    rp.data = array.array('c')
    for prop in properties:
        object = prop[0]
        instance = prop[1]
        property = prop[2]
        objID = tag.Context(0,data.BACnetObjectIdentifier(object,instance))
        if len(prop) < 4 or prop[3] == -1:
            propID =  tag.Construct(
                1,[tag.Context(0,data.encode_enumerated(property))]
                )
        else:
            arrayidx = prop[3]
            propID = tag.Construct(
                1,[tag.Context(0, data.encode_enumerated(property)),
                   tag.Context(1, data.encode_unsigned_integer(arrayidx))]
                )
        rp.data.fromstring(objID.encoding)
        rp.data.fromstring(propID.encoding)
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    responses = tag.decode(r.data)
    for response in responses.value:
        # Now if we felt like it, we could extract the BACnetIdentifierObject from
        # the response data, at response.number 0.  But we won't because
        # we don't need it at the moment.
        if response.number == 1:
            # Property id/value list.
            for p in response.value:
                #  Again, if we felt like it, we could extract the property
                #  ID from tag.number 2.  But we won't because we don't use
                #  it.  If we wrote code to match the request to response, 
                #  we would need it.
                if p.number == 4:
                    # Property value list
                    p_value = p.value[0].value
                    if p_value is None:
                        pass
                    p_bacnet_value_type = p.value[0].number
                    results.append((p_value, p_bacnet_value_type))
                elif p.number == 3:
                    # Property value list
                    p_value = p.value[0].value
                    p_bacnet_value_type = p.value[0].number
                    results.append((p_value, p_bacnet_value_type))
                elif p.number == 5:
                    # error code
                    results.append((None, None))
    return results

def read_property_multiple(device, properties):
    
    # this hack is back in now because Trane's onsite bridge (device 11)
    # does not properly answer multiple properties
    # This method first tries RPM, then RPM(singular) and finially RP to retrieve
    # a list of properties
    # A readPropertyFallback attribute remembers which mode was successful and
    # that is used in subsequent reads

    results=[]
    if (not (_device_table.has_key(device)) or \
        (_device_table[device].readPropertyFallback < 2)):
        results = read_property_multiple_real2(device,properties)
        if (results != None):
            if (len(results) == len(properties)): 
                _device_table[device].readPropertyFallback=1 # No fallback needed.
                return results
    # we did not get the result we expected, try to fall back to a different
    # method this function breaks the read_property_multiple into groups of
    # GroupSize
    results=[]
    Groupsize = 1
    while properties:
        group = properties[0:Groupsize]
        ilen = len(group)
        result = None
        
        if (_device_table[device].readPropertyFallback == 0) or \
           (_device_table[device].readPropertyFallback == 2):

            result = read_property_multiple_real2(device, group)

            if (result != None): #remember this worked
                if (_device_table[device].readPropertyFallback == 0):
                    msglog.log('broadway', msglog.types.WARN,
                               'read_property_multiple fallback for device = ' +
                               str(device))
                _device_table[device].readPropertyFallback = 2 # Use single RPM.

        if (_device_table[device].readPropertyFallback == 0) or \
           (_device_table[device].readPropertyFallback == 3):

            result = read_property(device, group[0])

            if (result != None): #remember this worked
                if (_device_table[device].readPropertyFallback == 0):
                    msglog.log('broadway', msglog.types.WARN,
                               'read_property fallback for device = ' +
                               str(device))    
                _device_table[device].readPropertyFallback = 3

                rp_result = result  #convert result to RPM style
                result = ((None, None),)
                for p in rp_result.value:
                    #  Again, if we felt like it, we could extract the property
                    #  ID from tag.number 2.  But we won't because we don't use
                    #  it.  If we wrote code to match the request to response, 
                    #  we would need it.
                    if p.number == 4:
                        # Property value list
                        p_value = p.value[0].value
                        p_bacnet_value_type = p.value[0].number
                        result = ((p_value, p_bacnet_value_type),)
                    elif p.number == 3:
                        # Property value list
                        p_value = p.value[0].value
                        p_bacnet_value_type = p.value[0].number
                        result = ((p_value, p_bacnet_value_type),)
                    elif p.number == 5:
                        # error code
                        result = ((None, None),)
        properties = properties[Groupsize:]
        if result is None:
            if DEBUG: print 'No results...'
            result = (None,None)
            for i in range(0,ilen):
                results.append(result)
        else:
            for i in range(0,ilen):
                if i < len(result):
                    results.append(result[i])
                else:
                    raise BACnetException('Too few results...')
    return results

##
# @fixme Decode the BACnet-SimpleACK-PDU?
def write_property_g3(device, prop_tuple, value_tag_list, priority=None):
    object = prop_tuple[0]
    instance = prop_tuple[1]
    property = prop_tuple[2]

    wpr = sequence.WritePropertyRequest()
    wpr.object_identifier = data.BACnetObjectIdentifier(object, instance)
    wpr.property_identifier = property
    if len(prop_tuple) > 3 and prop_tuple[3] != -1:
        wpr.property_array_index = prop_tuple[3]
    wpr.property_value = value_tag_list
    if priority is not None:
        wpr.priority = priority
    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 15
    rp.data = tag.encode(wpr.encoding)
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    return r

##
# @fixme Decode the BACnet-SimpleACK-PDU? (See note at end of function.)
# @fixme Use no_fall_back param in implementation of fallback code...
# Structure of prop_vals param:
# [[prop_tuple0, prop_value0], ..., [prop_tuple0, prop_value0]]
def write_property_multiple_g3(device, prop_vals, no_fall_back=0):
    obj_ids = {}
    for pv in prop_vals:
        prop_tuple = pv[0]
        prop_val = pv[1]        
        object = prop_tuple[0]
        instance = prop_tuple[1]
        k = (object, instance) # use tuple as key into object map
        if not obj_ids.has_key(k): # if necy, add a map entry for the given object ID
            was = sequence.WriteAccessSpecification()
            was.list_of_properties = [] # populated on this pass, and poss'ly subsequent passes
            was.object_identifier = data.BACnetObjectIdentifier(object, instance)
            obj_ids[k] = was
        property_id = prop_tuple[2]
        property_array_index = None # default
        priority = None             # default
        # If valid index and/or priority is/are available, add it/them to extended tuple:
        if len(prop_tuple) > 3 and prop_tuple[3] != -1:
            property_array_index = prop_tuple[3]
            if len(prop_tuple) > 4:
                priority = prop_tuple[4]
        # Create and init a new BACnetPropertyValue instance (using given value), and add
        # that new instance to the corresponding object map entry:
        kw = {'property_identifier':property_id,\
              'value':prop_val,\
              'property_array_index':property_array_index}
        if not property_array_index is None:
            kw['property_array_index'] = property_array_index
        if not priority is None:
            kw['priority'] = priority
        obj_ids[k].list_of_properties.append(sequence.BACnetPropertyValue(*(),**kw))
    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 16
    for obj_v in obj_ids.values():
        obj_v_enc = obj_v.encoding
        t = tag.encode(obj_v_enc)
        rp.data.fromstring(t)
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    
    # @fixme Decode the BACnet-SimpleACK-PDU? and/or handle error rtns by defaulting to
    # write_prop_mults on each "obj_v" above, and then to indiv write_props on elems of
    # obj_v.list_of_properties...
    return r

def server_write_property(device, msg):
    try:
        #device.time_wp.begin()
        request = tag.decode(msg.data)
        if DEBUG: print 'SERVER WRITE PROPERTY request: ', request
        s = sequence.WritePropertyRequest(decode=request.value)
        if DEBUG: print 'SERVER WRITE PROPERTY sequence: ', s
        o = device.find_bacnet_object(s.object_identifier)
        if o is None: # object not found
            raise ENotFound('BACnet Server Write, Object not found, Type: %d Instance: %d propID: %d' % \
                            (s.object_identifier.object_type, 
                             s.object_identifier.instance_number,
                             s.property_identifier))
        if DEBUG: print 'SERVER WRITE PROPERTY object: ', o
        p = o.find_property(s.property_identifier)
        if p is None: # object not found
            raise ENotFound('BACnet Server Write Prop not found, Type: %d Instance: %d propID: %d' % \
                            (s.object_identifier.object_type, 
                             s.object_identifier.instance_number,
                             s.property_identifier))
        if DEBUG: print 'SERVER WRITE PROPERTY property: ', p
        priority = None
        if s.priority != OPTIONAL:
            priority = s.priority
        i = None
        if s.property_array_index != OPTIONAL:
            i = s.property_array_index
        if DEBUG: print 'SERVER WRITE PROPERTY value: ', s.property_value[0].value, priority
        p.write(s.property_value, i, priority)
        answer = simple_ack_pdu(msg)
        #device.time_wp.end()
        return answer
    except EPermission:
        if DEBUG:
            print 'Permission error on write propety'
        return error_pdu(msg, 2, 40)
    except:
        msglog.exception()
        if DEBUG:
            print 'ERROR on Write Property'
            print 'device: ', str(device)
        return error_pdu(msg, 2, 0)

    
# @fixme Why not just send me an applicataion tag as the value?
# @fixme If nothing else, how 'bout consistant parameter with read?
def server_write_property_multiple(device, msg):
    request = tag.decode(msg.data)
    if DEBUG: print 'SERVER WRITE PROPERTY MULTIPLE request: ', request
    results = None
    #convert request into a list of read access specifications
    ss = sequence.context_write_access_specification_list(request)
    o = None
    p = None
    if DEBUG: print 'SERVER WRITE PROPERTY sequence: ', ss
    for s in ss: #do each write access specification
        o = device.find_bacnet_object(s.object_identifier)
        if DEBUG: print 'SERVER WRITE PROPERTY object: ', o
        for pv in s.list_of_properties:
            i = None
            if pv.property_array_index != OPTIONAL:
                i = pv.property_array_index
            priority = None
            if pv.priority != OPTIONAL:
                priority = pv.priority
            try:
                p = o.find_property(pv.property_identifier)
                p.write(pv.value, i, priority)  #index?
            except EPermission:
                if DEBUG: print 'SERVER WRITE PROPERTY EPERMISSION ERROR'
                result = sequence.WritePropertyMultipleError()
                result.error_type = sequence.Error(2,40) #write access denied
                bopr = BACnetObjectPropertyReference()
                bopr.object_identifier = s.object_identifier
                bopr.property_identifier = pv.property_identifier
                bopr.property_index = pv.property_array_index
                result.first_failed_write_attempt = bopr
                return complex_ack_pdu(result.encoding)
            except:
                if DEBUG: print 'SERVER WRITE PROPERTY ERROR'
                result = sequence.WritePropertyMultipleError()
                if p:
                    result.error_type = sequence.Error(2,25) #operational error
                elif o:
                    result.error_type = sequence.Error(2,32) #unknown property
                else: #unkown object
                    result.error_type = sequence.Error(1,31) #unknown object
                bopr = BACnetObjectPropertyReference()
                bopr.object_identifier = s.object_identifier
                bopr.property_identifier = pv.property_identifier
                bopr.property_index = pv.property_array_index
                result.first_failed_write_attempt = bopr
                return complex_ack_pdu(result.encoding)
            if DEBUG: print 'SERVER WRITE PROPERTY property: ', p
    return simple_ack_pdu(msg)
    
def write_property(device, object, instance, property, arrayidx, priority,
                   value, btype):
    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 15
    objectIdentifier = tag.Context(0,data.BACnetObjectIdentifier(object,instance))
    propertyIdentifier = tag.Context(1,data.encode_enumerated(property))
    propertyArrayIndex = None # @fixme Support arrayidx
    propertyValue = tag.Construct(3)
    if (priority):
        priorityTag = tag.Context(4,data.encode_enumerated(priority))
    
    if btype == 0:    propertyValue.value.append(tag.Null())
    elif btype == 1:  propertyValue.value.append(tag.Boolean(int(value)))
    elif btype == 2:  propertyValue.value.append(tag.UnsignedInteger(int(value)))
    elif btype == 3:  propertyValue.value.append(tag.SignedInteger(int(value)))
    elif btype == 4:  propertyValue.value.append(tag.Real(float(value)))
    elif btype == 5:  propertyValue.value.append(tag.Double(float(value)))
    elif btype == 6:  propertyValue.value.append(tag.OctetString(value))
    elif btype == 7:
        if type(value) == types.StringValue or type(value) == array.ArrayType:
            propertyValue.value.append(tag.CharacterString(data.ANSI_String(value)))
        else:
            propertyValue.value.append(tag.CharacterString(value))
    elif btype == 8:  propertyValue.value.append(tag.BitString(value))
    elif btype == 9:  propertyValue.value.append(tag.Enumerated(int(value)))
    elif btype == 10: propertyValue.value.append(tag.Date(value))
    elif btype == 11: propertyValue.value.append(tag.Time(value))
    elif btype == 12: propertyValue.value.append(tag.BACnetObjectIdentifier(value))
    else: raise EInvalidValue("btype", btype)

    if propertyArrayIndex is None:
        rp.data = objectIdentifier.encoding + propertyIdentifier.encoding + \
                  propertyValue.encoding
    else:
        rp.data = objectIdentifier.encoding + propertyIdentifier.encoding + \
                  propertyArrayIndex.encoding + propertyValue.encoding

    if (priority):  #optional priority tag
        rp.data = rp.data + priorityTag.encoding
        
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)
    return r

# @fixme Need to match id's requested with values returned from readpropertymultiple
def read_object_priority_array(device, object_type, object_instance):
    """##
    # Returns a 16 element list of priority values.  
    # @param device address number, object type number, object index.
    # @Returns a 16 element list.  Each entry cooresponds to a priority level
    # an entry of None means that level is not in use.  An entry with a value
    # indicates that priority's requested value.  The highest priority (lower number
    # is higher priority) with a value is the level in control"""
    results = []
    identifier_list = []
    answer = []
    last_instance = 0
    max_tags = 0
    
    responses = read_property(device, (object_type,
                                       object_instance,
                                       BACNET_PROPERTY_IDENTIFIER_PRIORITY_ARRAY))
    for response in responses.value:
        #   Now if we felt like it, we could extract the BACnetIdentifierObject from
        #   the response data, at response.number 0.  But we won't because
        #   we don't need it at the moment.
        if response.number == 3: #context 3 contains the array of priorities
            # reply parameters list.
            for p in response.value:
                answer.append(p.value) 
    #now create a read property multiple to request all the names of these collected id's
    return answer

def override_object(device, object_type, object_instance, priority, value):
    """##
    # Returns a 16 element list of priority values.  
    # @param device address number, object type number, object index.
    # @Returns a 16 element list.  Each entry cooresponds to a priority level
    # an entry of None means that level is not in use.  An entry with a value
    # indicates that priority's requested value.  The highest priority
    # (lower number
    # is higher priority) with a value is the level in control"""
    results = []
    identifier_list = []
    answer = []
    last_instance = 0
    max_tags = 0
    
    if   object_type == BACNET_OBJECT_TYPE_ANALOG_OUTPUT:     btype = 4
    elif object_type == BACNET_OBJECT_TYPE_ANALOG_VALUE:      btype = 4
    elif object_type == BACNET_OBJECT_TYPE_BINARY_OUTPUT:     btype = 9
    elif object_type == BACNET_OBJECT_TYPE_BINARY_VALUE:      btype = 9
    elif object_type == BACNET_OBJECT_TYPE_MULTISTATE_OUTPUT: btype = 3
    elif object_type == BACNET_OBJECT_TYPE_MULTISTATE_VALUE:  btype = 3
    else:
        btype = 9
        
    if (value is None):
        btype = 0  #relinquish override

    answer = write_property(device, object_type, object_instance, 
                            BACNET_PROPERTY_IDENTIFIER_PRESENT_VALUE, 
                            None, priority, value, btype)
    return answer
def send_device_time_syncronization(device, date, time, utc_flag=0):
    """
    device is an integer that specifies the device instance number
    date is the application tag for a bacnet date
    time is the application tag for a bacnet time
    """ 
    rp = npdu.NPDU()
    rp.version = 1
    rp.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 6
    if utc_flag:
        rp.choice = 9
    rp.data = date.encoding + time.encoding
    network.send_request(device, rp)
    return
def send_addr_time_syncronization(network_num, addr, date, time, utc_flag=0):
    """
    network_num is then integer network number
    addr is an Addr string
    date is the application tag for a bacnet date
    time is the application tag for a bacnet time
    """
    rp = npdu.NPDU()
    rp.version = 1
    rp.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 6
    if utc_flag:
        rp.choice = 9
    rp.dspec = 1
    rp.dlen = len(addr)
    rp.dnet = 0xffff
    rp.hop_count = 255
    rp.data = date.encoding + time.encoding
    network._send(network_num, addr, rp)
    return
# @fixme Need to match id's requested with values returned from readpropertymultiple
def read_private_object_list(device, vendor, object_type, start_index=0):
    """##
    # Return a list of lists of object names and identifiers.
    # @param device address number, vendor number, object type number.
    # @return A list, each element of which is a list with the first item an object name,
    #  the second item a BacnetObjectIndentifier object."""
    results = []
    identifier_list = []
    answer = []
    last_instance = 0
    max_tags = 0
    
    rp = APDU()
    rp.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
    rp.choice = 18 #ConfirmedPrivateTransferRequest 

    rp.data = array.array('c')
    vendorID = tag.Context(0,data.encode_unsigned_integer(vendor))
    service = tag.Context(1,data.encode_unsigned_integer(0x81))
    instanceTag = tag.Construct(2,[
        tag.Context(0,data.encode_unsigned_integer(object_type)),
        tag.Context(1,data.encode_unsigned_integer(start_index)),
        tag.Context(2,data.encode_unsigned_integer(50))])
                                
    rp.data.fromstring(vendorID.encoding)
    rp.data.fromstring(service.encoding)
    rp.data.fromstring(instanceTag.encoding)
        
    request_id = network.send_request(device, rp)
    r = recv_response(request_id)

    responses = tag.decode(r.data)
    for response in responses.value:
        #   Now if we felt like it, we could extract the BACnetIdentifierObject from
        #   the response data, at response.number 0.  But we won't because
        #   we don't need it at the moment.
        if response.number == 2: #context 2 contains instance tag replay parameters
            # reply parameters list.
            for p in response.value:
                #  we could match tag 0 with requested object type
                if p.number == 1:
                    #  last Instance retrieved
                    last_instance = data.BACnetObjectIdentifier(decode=p.data).instance_number
                if p.number == 2:
                    # Max tags returned.  If equals 50, ask for more
                    max_tags = ord(p.data)
                if p.number == 3: #yet another open context
                    # Identifier list
                    for i in p.value:
                        if i.number == 4: #this is the bacnet object identifier
                            # bnoi = data.data_decode_bacnet_object_identifier(i.data)
                            bnoi = data.BACnetObjectIdentifier(decode=i.data)
                            #finially we get to add one to the list
                            identifier_list.append(bnoi) 
                            #tag 5 would be theNVMTag, whatever that is
                            #tag 6 would be the VMTag

    #now create a read property multiple to request all the names of these collected id's
    properties = []
    if len(identifier_list) > 0:
        for id in identifier_list:
            properties.append([object_type,id.instance_number,77])
    
        try:
            answer = read_property_multiple(device, properties)
        except BACnetError, e:
            # @fixme Remove after we figure out the error.
            print e.npdu
            raise e
    
        if len(answer) != len(identifier_list):
            raise BACnetException('Identifier list and answer list are different lengths')
            
        for i in range(len(identifier_list)):
            results.append([device,identifier_list[i].object_type,
                            identifier_list[i].instance_number,
                            answer[i][0].character_string])
        if max_tags == 50:
            results = results.append(read_private_object_list(device,
                                                              vendor,
                                                              object_type,
                                                              last_instance))
    return results
