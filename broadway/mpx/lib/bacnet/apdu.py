"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
# Provides the application abstraction for BACnet networks.
#
# @todo Critical sections for shared, writeable data.
# @todo Global, unique, invoke_id management.
# @todo Invoke ID based dequeuing.
# @todo Pairing of requests and responses.
# @todo May need to schedule sending of APDUs w/o invoke IDs to assist pairing.
#       (queue mgmt by type?).
# @todo ACK/NAK retry logic.
# @todo Effecient waiting for responses.
# @todo Device ID based addressing (barp).
# @todo Use a tag registry to encode decode tags that are part of an APDUs
#       definition (handle optional stuff by registering a function to
#       insert/extract the tag and advance the 'tag pointer').

import array
import types

from mpx.lib.bacnet.npdu import NPDU, Addr
from mpx.lib.exceptions import *

#
# PDU Types
#
BACNET_CONFIRMED_SERVICE_REQUEST_PDU = 0
BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU = 1
BACNET_SIMPLE_ACK_PDU = 2
BACNET_COMPLEX_ACK_PDU = 3
BACNET_SEGMENT_ACK_PDU = 4
BACNET_ERROR_PDU = 5
BACNET_REJECT_PDU = 6
BACNET_ABORT_PDU = 7

#
# BACnetUnconfirmedServiceChoice ::= ENUMERATED
# ASHRAE 135-1995 21. (page 359)
#
I_AM_CHOICE = 0
I_HAVE_CHOICE = 1
UNCONFIRMED_COV_NOTIFICATION_CHOICE = 2
UNCONFIRMED_EVENT_NOTIFICATION_CHOICE = 3
UNCONFIRMED_PRIVATE_TRANSFER_CHOICE = 4
UNCONFIRMED_TEXT_MESSAGE_CHOICE = 5
TIME_SYNCHRONIZATION_CHOICE = 6
WHO_HAS_CHOICE = 7
WHO_IS_CHOICE = 8

#
# BACnet-Unconfirmed-Service-Request ::= CHOICE
# ASHRAE 135-1995 21. (page 359)
#
I_AM_REQUEST = 0
I_HAVE_REQUEST = 1
UNCONFIRMED_COV_NOTIFICATION_REQUEST = 2
UNCONFIRMED_EVENT_NOTIFICATION_REQUEST = 3
UNCONFIRMED_PRIVATE_TRANSFER_REQUEST = 4
UNCONFIRMED_TEXT_MESSAGE_REQUEST = 5
TIME_SYNCHRONIZATION_REQUEST = 6
WHO_HAS_REQUEST = 7
WHO_IS_REQUEST = 8

#
# BACnetAbortReason ::= ENUMERATED
# ASHRAE 135-1995 21. (page 361)
#
ABORT_REASON_OTHER = 0
ABORT_REASON_BUFFER_OVERFLOW = 1
ABORT_REASON_INVALID_APDU_IN_THIS_STATE = 2
ABORT_REASON_PREEMPTED_BY_HIGHER_PRIORITY_TASK = 3
ABORT_REASON_SEGMENTATION_NOT_SUPPORTED = 4

#
# BACnetRejectReason ::= ENUMERATED
# ASHRAE 135-1995 21. (page 362)
#
REJECT_REASON_OTHER = 0
REJECT_REASON_BUFFER_OVERFLOW = 1
REJECT_REASON_INCONSISTENT_PARAMETERS = 2
REJECT_REASON_INVALID_PARAMETER_DATA_TYPE = 3
REJECT_REASON_INVALID_TAG = 4
REJECT_REASON_MISSING_REQUIRED_PARAMETER = 5
REJECT_REASON_PARAMETER_OUT_OF_RANGE = 6
REJECT_REASON_TOO_MANY_ARGUMENTS = 7
REJECT_REASON_UNDEFINED_ENUMERATION = 8
REJECT_REASON_UNRECOGNIZED_SERVICE = 9

#
# error-class ::= ENUMERATED
# ASHRAE 135-1995 21. (page 363)
#
ERROR_CLASS_DEVICE = 0
ERROR_CLASS_OBJECT = 1
ERROR_CLASS_PROPERTY = 2
ERROR_CLASS_RESOURCES = 3
ERROR_CLASS_SECURITY = 4
ERROR_CLASS_SERVICES = 5
ERROR_CLASS_VT = 6

#
# error-code ::= ENUMERATED
# ASHRAE 135-1995 21. (page 363)
#
ERROR_CODE_OTHER = 0
ERROR_CODE_AUTHENTICATION_FAILED = 1
ERROR_CODE_CHARACTER_SET_NOT_SUPPORTED = 41
ERROR_CODE_CONFIGURATION_IN_PROGRESS = 2
ERROR_CODE_DEVICE_BUSY = 3
ERROR_CODE_DYNAMIC_CREATION_NOT_SUPPORTED = 4
ERROR_CODE_FILE_ACCESS_DENIED = 5
ERROR_CODE_INCOMPATIBLE_SECURITY_LEVELS = 6
ERROR_CODE_INCONSISTENT_PARAMETERS = 7
ERROR_CODE_INCONSISTENT_SELECTION_CRITERION = 8
ERROR_CODE_INVALID_ARRAY_INDEX = 42
ERROR_CODE_INVALID_CONFIGURATION_DATA = 46
ERROR_CODE_INVALID_DATA_TYPE = 9
ERROR_CODE_INVALID_FILE_ACCESS_METHOD = 10
ERROR_CODE_INVALID_FILE_START_POSITION = 11
ERROR_CODE_INVALID_OPERATOR_NAME = 12
ERROR_CODE_INVALID_PARAMETER_DATA_TYPE = 13
ERROR_CODE_INVALID_TIME_STAMP = 14
ERROR_CODE_KEY_GENERATION_ERROR = 15
ERROR_CODE_MISSING_REQUIRED_PARAMETER = 16
ERROR_CODE_NO_OBJECTS_OF_SPECIFIED_TYPE = 17
ERROR_CODE_NO_SPACE_FOR_OBJECT = 18
ERROR_CODE_NO_SPACE_TO_ADD_LIST_ELEMENT = 19
ERROR_CODE_NO_SPACE_TO_WRITE_PROPERTY = 20
ERROR_CODE_NO_VT_SESSIONS_AVAILABLE = 21
ERROR_CODE_OBJECT_DELETION_NOT_PERMITTED = 23
ERROR_CODE_OBJECT_IDENTIFIER_ALREADY_EXISTS = 24
ERROR_CODE_OPERATIONAL_PROBLEM = 25
ERROR_CODE_OPTIONAL_FUNCTIONALITY_NOT_SUPPORTED = 45
ERROR_CODE_PASSWORD_FAILURE = 26
ERROR_CODE_PROPERTY_IS_NOT_A_LIST = 22
ERROR_CODE_READ_ACCESS_DENIED = 27
ERROR_CODE_SECURITY_NOT_SUPPORTED = 28
ERROR_CODE_SERVICE_REQUEST_DENIED = 29
ERROR_CODE_TIMEOUT = 30
ERROR_CODE_UNKNOWN_OBJECT = 31
ERROR_CODE_UNKNOWN_PROPERTY = 32
ERROR_CODE_UNKNOWN_VT_CLASS = 34
ERROR_CODE_UNKNOWN_VT_SESSION = 35
ERROR_CODE_UNSUPPORTED_OBJECT_TYPE = 36
ERROR_CODE_VALUE_OUT_OF_RANGE = 37
ERROR_CODE_VT_SESSION_ALREADY_CLOSED = 38
ERROR_CODE_VT_SESSION_TERMINATION_FAILURE = 39
ERROR_CODE_WRITE_ACCESS_DENIED = 40

_pdu_description_text = """\
PDU Type: %s (%d)
Implemented in %s
Defined in ASHRAE 135-1995 %s"""

class _NotImplemented:
    pass

class _PDU_Description:
    def __init__(self, pdu_type, pdu_name, pdu_definition, pdu_class):
        self.pdu_type  = pdu_type
        self.pdu_name  = pdu_name
        self.pdu_class = pdu_class
        self.pdu_definition = pdu_definition
    def __str__(self):
        return _pdu_description_text % (self.pdu_name, self.pdu_type,
                                        self.pdu_class.__name__,
                                        self.pdu_definition)
_pdu_map = {
    BACNET_CONFIRMED_SERVICE_REQUEST_PDU :
    _PDU_Description(BACNET_CONFIRMED_SERVICE_REQUEST_PDU,
                     'BACnet-Confirmed-Service-Request-PDU',
                     '20.1.2',
                     _NotImplemented),
    BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU :
    _PDU_Description(BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU,
                     'BACnet-Unconfirmed-Service-Request-PDU',
                     '20.1.3',
                     _NotImplemented),
    BACNET_SIMPLE_ACK_PDU : 
    _PDU_Description(BACNET_SIMPLE_ACK_PDU,
                     'BACnet-SimpleACK-PDU',
                     '20.1.4',
                     _NotImplemented),
    BACNET_COMPLEX_ACK_PDU :
    _PDU_Description(BACNET_COMPLEX_ACK_PDU,
                     'BACnet-ComplexACK-PDU',
                     '20.1.5',
                     _NotImplemented),
    BACNET_SEGMENT_ACK_PDU :
    _PDU_Description(BACNET_SEGMENT_ACK_PDU,
                     'BACnet-SegmentACK-PDU',
                     '20.1.6',
                     _NotImplemented),
    BACNET_ERROR_PDU :
    _PDU_Description(BACNET_ERROR_PDU,
                     'BACnet-Error-PDU',
                     '20.1.7',
                     _NotImplemented),
    BACNET_REJECT_PDU :
    _PDU_Description(BACNET_REJECT_PDU,
                     'BACnet-Reject-PDU',
                     '20.1.8',
                     _NotImplemented),
    BACNET_ABORT_PDU :
    _PDU_Description(BACNET_ABORT_PDU,
                     'BACnet-Abort-PDU',
                     '20.1.9',
                     _NotImplemented),
}

def _describe(pdu_type):
    return _pdu_map[pdu_type]

##
# Base class for BACnet APDUs.  This class behaves exactly like an NPDU
# except there is no limit to the amount of data it can contain.
#
# @note As a current implementation detail, the data is stored in a Python
# array.array('c') instance.  Because of this, you must use array methods
# to modify the contents of the data attribute.
#
# @fixme Make efficient use of the NPDU's data buffer instead of
#        copying memory around.
class APDU:
    ##
    # This class attribute is so npdu.is_NPDU will return true for APDUs
    # (as if APDU derived from NPDU).
    _is_NPDU = 1

    def __init__(self, npdu=None):
        # Since self._npdu is used in __getattr__ and __setattr__, it must
        # be added directly to the instance's attribute dictionary.
        if npdu:
            self.__dict__['_npdu'] = npdu
            self.__dict__['data'] = array.array('c', npdu.data)
        else:
            self.__dict__['_npdu'] = NPDU()
            self.__dict__['data'] = array.array('c')
        ##
        # The list of application tags for the PDU.
        self.tags = []
    ##
    # Behave as if we have all the attributes on our NPDU instance.
    def __getattr__(self, attr):
        return getattr(self._npdu, attr)
    ##
    # Behave as if we have all the attributes on our NPDU instance.
    def __setattr__(self, attr, value):
        if attr != 'data' and hasattr(self._npdu, attr):
            return setattr(self._npdu, attr, value)
        self.__dict__[attr] = value

    def as_npdu(self):
        if type(self.data) != types.StringType:
            self.data=self.data.tostring()
        if type(self.data) != types.StringType:
            raise EInvalidValue('unable to get string type:', type(self.data))
        self._npdu.data = self.data
        return self._npdu
##
# @return True if the <code>instance</code> is of the APDU class or any
#         class derived from <code>APDU</code>.
def is_APDU(instance):
    return isinstance(instance, APDU)

class BACnetConfirmedServiceRequestAPDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type                    [0] Unsigned (0..15),--0 for this PDU type
        self.pdu_type = BACNET_CONFIRMED_SERVICE_REQUEST_PDU
        # segmented-message           [1] BOOLEAN,
        self.segmented_message
        # more-follows                [2] BOOLEAN,
        self.more_follows
        # segmented-response-accepted [3] BOOLEAN
        self.segmented_response_accepted
        # reserved                    [4] Unsigned (0..3),-- must be set to zero
        # max-segments-accepted       [5] Unsigned (0..7),-- as per 20.1.2.4
        #                                 -- Not implemented yet ASHRAE 135-2001
        # max-APDU-length-accepted    [6] Unsigned (0..15), -- as per 20.1.2.5
        self.max_apdu_length_accepted
        # invokeID                    [7] Unsigned (0..255),
        self.invoke_id
        # sequence-number             [8] Unsigned (0..255) OPTIONAL,
        #                                 -- only if segmented msg
        self.sequence_number
        # proposed-window-size        [9] Unsigned (1..127) OPTIONAL,
        #                                 -- only if segmented msg
        self.window_size # @todo Verify this is proposed-window-size.
        # service-choice              [10] BACnetConfirmedServiceChoice,
        self.choice
        # service-request             [11] BACnet-Confirmed-Service-Request

class BACnetUnconfirmedServiceRequestAPDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type                    [0] Unsigned (0..15),--1 for this PDU type
        self.pdu_type = BACNET_UNCONFIRMED_SERVICE_REQUEST_PDU
        # reserved                    [1] Unsigned (0..15),--must be set to zero
        # service-choice              [2] BACnetUnconfirmedServiceChoice,
        self.choice
        # service-request             [3] BACnet-Unconfirmed-Service-Request

class BACnetSimpleACK_APDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type                    [0] Unsigned (0..15),--2 for this PDU type
        self.pdu_type = BACNET_SIMPLE_ACK_PDU
        # reserved                    [1] Unsigned (0..15),--must be set to zero
        # original-invokeID           [2] Unsigned (0..255),
        self.invoke_id
        # service-ACK-choice          [3] BACnetConfirmedServiceChoice
        self.choice

class BACnetComplexACK_APDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type                    [0] Unsigned (0..15),--3 for this PDU type
        self.pdu_type = BACNET_COMPLEX_ACK_PDU
        # segmented-message           [1] BOOLEAN,
        self.segmented_message
        # more-follows                [2] BOOLEAN,
        self.more_follows
        # original-invokeID           [4] Unsigned (0..255),
        self.invoke_id
        # sequence-number             [5] Unsigned (0..255) OPTIONAL,
        #                                 -- only if segmented msg
        self.sequence_number
        # proposed-window-size        [6] Unsigned (1..127) OPTIONAL,
        #                                 -- only if segmented msg
        self.window_size # @todo Verify this is proposed-window-size.
        # service-ACK-choice          [7] BACnetConfirmedServiceChoice,
        self.choice
        # service-ACK                 [8] BACnet-Confirmed-Service-ACK

class BACnetSegmentACK_APDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type           [0] Unsigned (0..15), -- 4 for this PDU type
        self.pdu_type = BACNET_SEGMENT_ACK_PDU
        # reserved           [1] Unsigned (0..3), -- must be set to zero
        # negative-ACK       [2] BOOLEAN,
        self.negative_ack
        # server             [3] BOOLEAN,
        self.server
        # original-invokeID  [4] Unsigned (0..255),
        self.invoke_id
        # sequence-number    [5] Unsigned (0..255),
        self.sequence_number
        # actual-window-size [6] Unsigned (1..127)
        self.window_size # @todo Verify this is actual-window-size.

class BACnetErrorAPDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type           [0] Unsigned (0..15), -- 5 for this PDU type
        self.pdu_type = BACNET_ERROR_PDU
        # reserved           [1] Unsigned (0..15), -- must be set to zero
        # original-invokeID  [2] Unsigned (0..255),
        self.invoke_id
        # error-choice       [3] BACnetConfirmedServiceChoice,
        self.choice
        # error              [4] BACnet-Error

class BACnetRejectAPDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type          [0] Unsigned (0..15), -- 6 for this PDU type
        self.pdu_type = BACNET_REJECT_PDU
        # reserved          [1] Unsigned (0..15), -- must be set to zero
        # original-invokeID [2] Unsigned (0..255),
        self.invoke_id
        # reject-reason     [3] BACnetRejectReason
        self.reason

class BACnetAbortAPDU(APDU):
    def __init__(self, npdu=None):
        APDU.__init__(self,npdu)
        # pdu-type           [0] Unsigned (0..15), -- 7 for this PDU type
        self.pdu_type = BACNET_ABORT_PDU
        # reserved           [1] Unsigned (0..7), -- must be set to zero
        # server             [2] BOOLEAN,
        self.server
        # original-invokeID  [3] Unsigned (0..255),
        self.invoke_id
        # abort-reason       [4] BACnetAbortReason
        self.reason
