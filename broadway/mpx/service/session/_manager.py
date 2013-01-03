"""
Copyright (C) 2002 2003 2006 2007 2009 2010 2011 Cisco Systems

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
import types
import weakref
from threading import Lock
from mpx import properties
from mpx.lib import msglog
from mpx.lib.uuid import UUID
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.node import ServiceNode
from mpx.lib.thread_pool import NORMAL
from mpx.lib.scheduler import scheduler
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.exceptions import MpxException
from mpx.lib.persistent import PersistentDataObject
from mpx.lib.persistence.datatypes import PersistentDictionary
from mpx.lib.user import _User as _User
from mpx.service.user_manager import EAuthenticationFailed
from mpx.service.security.user import User as User

class ESession(MpxException):
    pass

class ESessionDenied(ESession):
    pass

class Session(object):
    _VERSION = 1
    _VERSION_KW = 'version'
    _SESSION_ID_KW = 'session_id'
    _TTL_KW = 'ttl'
    _USERNAME_KW = 'username'
    _PASSWORD_KW = 'password'
    _LAST_ACCESS_KW = 'last_access'
    _ATTRIBUTES = (_VERSION_KW, _SESSION_ID_KW, _TTL_KW, _USERNAME_KW,
                   _PASSWORD_KW, _LAST_ACCESS_KW)
    _OPTIONAL = (_VERSION_KW, _LAST_ACCESS_KW)
    _STRING_TYPES = types.StringTypes
    _NUMBER_TYPES = (types.IntType, types.FloatType, types.LongType)
    def encode(session):
        return repr(session)
    encode = staticmethod(encode)
    def decode(data):
        return eval(data)
    decode = staticmethod(decode)
    def __init__(self, **keywords):
        _missing = []
        # Set default values.
        self.version = self._VERSION
        self.last_access = time.time()
        # Extract the attributes from the keywords.
        for attribute in (self._ATTRIBUTES):
            if keywords.has_key(attribute):
                setattr(self, attribute, keywords[attribute])
            else:
                if attribute not in self._OPTIONAL:
                    _missing.append(attribute)
        assert not _missing, (
            "The required attributes %r are missing" % _missing)
        assert type(self.version) is types.IntType, (
            "version must be a simple integer, not a %r." % type(self.version))
        assert type(self.session_id) in self._STRING_TYPES, (
            "session_id must be a string.")
        assert type(self.ttl) in self._NUMBER_TYPES, (
            "ttl must be a number.")
        assert (isinstance(self.username, User) or 
                type(self.username) in self._STRING_TYPES), (
            "username must be a string.")
        assert (self.password is None or
                type(self.password) in self._STRING_TYPES), (
            "password must be None or a string.")
        assert type(self.last_access) in self._NUMBER_TYPES, (
            "last_access must be a number.")
        # Calculate the expiration time.
        self.touch()
        super(Session, self).__init__()
    def __repr__(self):
        result = "Session("
        for attribute in self._ATTRIBUTES:
            if attribute == self._PASSWORD_KW:
                # Do not save the password.
                result = "%s%s=%r," % (result, attribute, None)
            else:
                result = "%s%s=%r," % (result, attribute,
                                       getattr(self, attribute))
        result = "%s)" % (result,)
        return result
    ##
    # Update the session's last_access time, which should defer the pending
    # expiration.
    def touch(self):
        self.last_access = time.time()
        self._expiration_time = self.last_access + self.ttl
        return self._expiration_time
    ##
    # @return When the session will expire if it is not accessed again.
    def expiration_time(self):
        return self._expiration_time
    ##
    # @return True if the session has not expired, false otherwise.
    def valid(self):
        return time.time() <= self._expiration_time

##
# @fixme Auto-save probably needs to be a bit more frequent.  Currently,
#        auto-save occurs when a new session is created and when the
#        "collector" runs (which is only when the session manager believes
#        that a session "may" have timedout).
class SessionManager(ServiceNode):
    import string
    IDCHARS = string.ascii_letters + string.digits 
    NCHARS  = len(IDCHARS)
    IDLEN = 20
    ETC_DIR=properties.ETC_DIR
    def __init__(self):
        self.ttl = 3600
        self._lock = Lock()
        self._sessions = None
        self._scheduled = None
        self.user_manager = None
        ServiceNode.__init__(self)
    def _begin_critical_section(self):
        self._lock.acquire()
    def _end_critical_section(self):
        self._lock.release()
    def _random_id(self):
        return str(UUID())
    def _next_session_id(self):
        sid = self._random_id()
        while self._sessions.has_key(sid):
            sid = self._random_id()
        return sid
    def start(self):
        self._begin_critical_section()
        try:
            if self._sessions is None:
                self._sessions = PersistentDictionary(self.name, 
                                                      encode=Session.encode, 
                                                      decode=Session.decode)
            if not self._scheduled:
                self._scheduled = scheduler.every(self.ttl, self.collect)
        finally:
            self._end_critical_section()
        self.user_manager = as_node("/services/User Manager")
        return ServiceNode.start(self)
    def stop(self):
        self._begin_critical_section()
        try:
            if self._scheduled:
                self._scheduled.cancel()
            self._scheduled = None
            self._sessions = None
        finally:
            self._end_critical_section()
        self.user_manager = None
        return ServiceNode.stop(self)
    def configure(self, cd):
        ServiceNode.configure(self, cd)
        set_attribute(self, 'ttl', self.ttl, cd, float)
        self.enabled = 1
    def configuration(self):
        cd = ServiceNode.configuration(self)
        get_attribute(self, 'ttl', cd, str)
        return cd
    ##
    # @fixme Use mpx.lib.security.User, as soon as it exists.
    # @fixme Cache mediator users...
    # @param nocheck Since we do not use shadow pass, the check can fail
    #                This is used to allow for bypass of check (for testing)
    # @exception ESessionDenied Raised when the SessionManager rejects
    #            creating the session because the request is not valid.
    #            In other words, the username or password are incorrect
    #            or there is some other aspect of the request which is
    #            not acceptable to the SessionManager.
    def create(self, user, password=None):
        if not isinstance(user, User):
            if properties.get_boolean('PAM_ENABLE'):
                authenticator = self.user_manager.user_from_pam
            else:
                authenticator = self.user_manager.user_from_cleartext
            try:
                user = authenticator(user, password)
            except EAuthenticationFailed:
                raise ESessionDenied("User credentials invalid.")
        self._begin_critical_section()
        try:
            sid = self._next_session_id()
            username = None
            if isinstance(user, User): username = user.name
            if isinstance(user, _User): username = user.name()
            self._sessions[sid] = Session(session_id=sid, 
                                          ttl=self.ttl, 
                                          username=username, 
                                          password=password)
        finally:
            self._end_critical_section()
        return sid
    ##
    # Immediately invalidate a session.
    # @param session_id The string that identifies the session to invalidate.
    def destroy(self, session_id):
        self._begin_critical_section()
        try:
            removed = self._sessions.pop(session_id)
            del self._sessions[session_id]
        except KeyError:
            removed = False
        finally:
            self._end_critical_section()
        return removed
    ##
    # Checks if a session_id is in the list of valid sessions.
    # @param session_id The string that identifies the session.
    # @param touch If true, and the session exists, then the session's
    #        last_access time will be updated.
    # @return True if the session_id is currently valid.
    # @note The implementation assumes that if a session_id is in the list of
    #       managed sessions, then it is valid.  It is the responsibility of
    #       the "auto collection" mechanism to remove expired sessions in a
    #       timely fashon.
    def validate(self, session_id, touch=0):
        self._begin_critical_section()
        try:
            session = self._sessions.get(session_id)
            if session and session.valid():
                if touch:
                    session.touch()
                valid = True
            else:
                valid = False
        finally:
            self._end_critical_section()
        return valid
    ##
    # Scan all managed sessions for expired sessions.
    # @return The number of expired sessions invalidated by this invocation.
    def collect(self):
        sessions = self._sessions
        self._begin_critical_section()
        try:
            sids = [sid for sid,ses in sessions.items() if not ses.valid()]
        finally:
            self._end_critical_section()
        for sid in sids:
            self.destroy(sid)
        return sids
    ##
    # Look up the user associated with a session
    # @return A string representing the user associated with this session.
    def get_user_from_sid(self, sid):
        user = None
        session = self._sessions.get(str(sid))
        if session:
            try:
                user = self.user_manager.get_user(session.username)
            except:
                msglog.exception(prefix="handled")
        return user

    ##
    # Look up the user associated with a session
    # @return True or False according to the user existence in session.
    def is_user_active(self, username):
        for sid in self._sessions:
            if self._sessions[sid].username == username:
                return True
        return False
