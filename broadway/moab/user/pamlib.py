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
from ctypes import CDLL
from ctypes import c_char_p

from mpx.lib.exceptions import MpxException

##
#  @return the absolute path to _pamlib.so assuming it is in the same
#          directory as this file.
def _pamlib_abspath():
    return os.path.join(os.path.dirname(
            os.path.abspath(__file__)), '_pamlib.so')

# Get ctypes reference to _pamlib.so
_cdll = CDLL(_pamlib_abspath())

##
# @return the string representation
def pam_error_tostr(errcode):
    _cdll._pam_error.restype = c_char_p
    return _cdll._pam_error(errcode)

##
# Test validity of USERNAME and PASSWORD.  Returns if they are valid
# credentials, otherwise raises the appropriate error.
def validate(username, password):
    retval = _cdll.validate(username, password)
    if retval:
        raise PAMError.new(retval)
    return

##
# PAMError: Class from which all PAM specific exceptions are derived.
class PAMError(MpxException):
    errcode = -1
    _class_map = {}
    def __init__(self,*args):
        self.errstr = pam_error_tostr(self.errcode)
        MpxException.__init__(self, self.errstr)
        return
    def learn(cls,exc):
        cls._class_map[exc.errcode] = exc
    learn = classmethod(learn)
    def new(cls,errcode):
        return cls._class_map.get(errcode,cls)(errcode)
    new = classmethod(new)

#
# Define PAM errcodes, define and "register" matching exceptions.
#

# Successful function return
PAM_SUCCESS = 0

# dlopen() failure when dynamically loading a service module
PAM_OPEN_ERR = 1
class EPAMOpenErr(PAMError): errcode = PAM_OPEN_ERR
PAMError.learn(EPAMOpenErr)

# Symbol not found
PAM_SYMBOL_ERR = 2
class EPAMSymbolErr(PAMError): errcode = PAM_SYMBOL_ERR
PAMError.learn(EPAMSymbolErr)

# Error in service module
PAM_SERVICE_ERR = 3
class EPAMServiceErr(PAMError): errcode = PAM_SERVICE_ERR
PAMError.learn(EPAMServiceErr)

# System error
PAM_SYSTEM_ERR = 4
class EPAMSystemErr(PAMError): errcode = PAM_SYSTEM_ERR
PAMError.learn(EPAMSystemErr)

# Memory buffer error
PAM_BUF_ERR = 5
class EPAMBufErr(PAMError): errcode = PAM_BUF_ERR
PAMError.learn(EPAMBufErr)

# Permission denied
PAM_PERM_DENIED = 6
class EPAMPermDenied(PAMError): errcode = PAM_PERM_DENIED
PAMError.learn(EPAMPermDenied)

# Authentication failure
PAM_AUTH_ERR = 7
class EPAMAuthErr(PAMError): errcode = PAM_AUTH_ERR
PAMError.learn(EPAMAuthErr)

# Can not access authentication data due to insufficient credentials
PAM_CRED_INSUFFICIENT = 8
class EPAMCredInsufficient(PAMError): errcode = PAM_CRED_INSUFFICIENT
PAMError.learn(EPAMCredInsufficient)

# Underlying authentication service can not retrieve authentication
# information
PAM_AUTHINFO_UNAVAIL = 9
class EPAMAuthInfoUnavail(PAMError): errcode = PAM_AUTHINFO_UNAVAIL
PAMError.learn(EPAMAuthInfoUnavail)

# User not known to the underlying authenticaiton module
PAM_USER_UNKNOWN = 10
class EPAMUserUnknown(PAMError): errcode = PAM_USER_UNKNOWN
PAMError.learn(EPAMUserUnknown)

# An authentication service has maintained a retry count which has been
# reached.  No further retries should be attempted
PAM_MAXTRIES = 11
class EPAMMaxTries(PAMError): errcode = PAM_MAXTRIES
PAMError.learn(EPAMMaxTries)

# New authentication token required. This is normally returned if the machine
# security policies require that the password should be changed beccause the
# password is NULL or it has aged
PAM_NEW_AUTHTOK_REQD = 12
class EPAMNewAuthTokReqd(PAMError): errcode = PAM_NEW_AUTHTOK_REQD
PAMError.learn(EPAMNewAuthTokReqd)

# User account has expired
PAM_ACCT_EXPIRED = 13
class EPAMAcctExpired(PAMError): errcode = PAM_ACCT_EXPIRED
PAMError.learn(EPAMAcctExpired)

# Can not make/remove an entry for the specified session
PAM_SESSION_ERR = 14
class EPAMSessionErr(PAMError): errcode = PAM_SESSION_ERR
PAMError.learn(EPAMSessionErr)

# Underlying authentication service can not retrieve user credentials
# unavailable
PAM_CRED_UNAVAIL = 15
class EPAMCredUnavail(PAMError): errcode = PAM_CRED_UNAVAIL
PAMError.learn(EPAMCredUnavail)

# User credentials expired
PAM_CRED_EXPIRED = 16
class EPAMCredExpired(PAMError): errcode = PAM_CRED_EXPIRED
PAMError.learn(EPAMCredExpired)

# Failure setting user credentials
PAM_CRED_ERR = 17
class EPAMCredErr(PAMError): errcode = PAM_CRED_ERR
PAMError.learn(EPAMCredErr)

# No module specific data is present
PAM_NO_MODULE_DATA = 18
class EPAMNoModuleData(PAMError): errcode = PAM_NO_MODULE_DATA
PAMError.learn(EPAMNoModuleData)

# Conversation error
PAM_CONV_ERR = 19
class EPAMConvErr(PAMError): errcode = PAM_CONV_ERR
PAMError.learn(EPAMConvErr)

# Authentication token manipulation error
PAM_AUTHTOK_ERR = 20
class EPAMAuthTokErr(PAMError): errcode = PAM_AUTHTOK_ERR
PAMError.learn(EPAMAuthTokErr)

# Authentication information cannot be recovered
PAM_AUTHTOK_RECOVERY_ERR = 21
class EPAMAuthTokRecoveryErr(PAMError): errcode = PAM_AUTHTOK_RECOVERY_ERR
PAMError.learn(EPAMAuthTokRecoveryErr)

# Authentication token lock busy
PAM_AUTHTOK_LOCK_BUSY = 22
class EPAMAuthTokLockBusy(PAMError): errcode = PAM_AUTHTOK_LOCK_BUSY
PAMError.learn(EPAMAuthTokLockBusy)

# Authentication token aging disabled
PAM_AUTHTOK_DISABLE_AGING = 23
class EPAMAuthTokDisableAging(PAMError): errcode = PAM_AUTHTOK_DISABLE_AGING
PAMError.learn(EPAMAuthTokDisableAging)

# Preliminary check by password service
PAM_TRY_AGAIN = 24
class EPAMTryAgain(PAMError): errcode = PAM_TRY_AGAIN
PAMError.learn(EPAMTryAgain)

# Ignore underlying account module regardless of whether the control flag is
# required, optional, or sufficient
PAM_IGNORE = 25
class EPAMIgnore(PAMError): errcode = PAM_IGNORE
PAMError.learn(EPAMIgnore)

# Critical error (?module fail now request)
PAM_ABORT = 26
class EPAMAbort(PAMError): errcode = PAM_ABORT
PAMError.learn(EPAMAbort)

# user's authentication token has expired
PAM_AUTHTOK_EXPIRED = 27
class EPAMAuthTokExpired(PAMError): errcode = PAM_AUTHTOK_EXPIRED
PAMError.learn(EPAMAuthTokExpired)

# module is not known
PAM_MODULE_UNKNOWN = 28
class EPAMModuleUnknown(PAMError): errcode = PAM_MODULE_UNKNOWN
PAMError.learn(EPAMModuleUnknown)

# Bad item passed to pam_*_item()
PAM_BAD_ITEM = 29
class EPAMBadItem(PAMError): errcode = PAM_BAD_ITEM
PAMError.learn(EPAMBadItem)

# conversation function is event driven and data is not available yet
PAM_CONV_AGAIN = 30
class EPAMConvAgain(PAMError): errcode = PAM_CONV_AGAIN
PAMError.learn(EPAMConvAgain)

# please call this function again to complete authentication stack. Before
# calling again, verify that conversation is completed
PAM_INCOMPLETE = 31
class EPAMIncomplete(PAMError): errcode = PAM_INCOMPLETE
PAMError.learn(EPAMIncomplete)
