"""
Copyright (C) 2003 2004 2009 2010 2011 Cisco Systems

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
import md5
import mpx.lib # Bootstraping...
from mpx.lib.user import User
from moab.user.manager import PASSWD_FILE
from mpx.lib.exceptions import MpxException, ENotImplemented, EInvalidValue
from mpx.service import ServiceNode
from mpx.lib.threading import Lock
from mpx.lib.uuid import UUID
from mpx import properties as Properties
from mpx.lib import msglog
from mpx.lib.msglog.types import WARN, ERR
import os
from moab.user import pamlib

##
# Class from which all UserManager specific exceptions are
# derived.
class EUserManager(MpxException):
    pass
class EAuthenticationFailed(EUserManager):
    pass
class CacheableAuthenticator(object):
    def __init__(self, user, **keywords):
        self.user = user
        self.__minimizable = 1
        self.authenticate(**keywords)
    ##
    # Class method that returns the name of the user.
    def name(klass, **keywords):
        return keywords['name']
    name = classmethod(name)
    ##
    # Calculates key that matches currently cached key.
    # @note  This is what was returned by next_key last time
    #        a set of keywords were passed in.
    def current_key(klass, **keywords):
        return "%s:%s" % (klass.__name__, klass.current_id(**keywords))
    current_key = classmethod(current_key)
    ##
    # Calculates uniqued id that matches currently cached id.
    def current_id(klass,**keywords):
        raise ENotImplemented(klass.current_id)
    current_id = classmethod(current_id)
    ##
    # Calculates key that next set of keywords will match.
    def next_key(self):
        return '%s:%s' % (self.__class__.__name__,self.next_id())
    ##
    # Calculates unique id that next set of keywords will match.
    def next_id(self):
        return self.current_id(**self.keywords())
    ##
    # Get the keywords that are currently being used for this Authenticator.
    def keywords(self):
        return self._keywords
    ##
    # Validate the implementation specific credentials against this
    # authenticator.
    def validate(self, **keywords):
        if not keywords:
            keywords = self.keywords()
        else:
            self._keywords = keywords
        self._validate()
        return
    def authenticate(self,**keywords):
        if not keywords:
            keywords = self.keywords()
        else:
            self._keywords = keywords
        self._authenticate()
        return
    ##
    # @return True if the CacheableAuthenticator has reason to beliave that
    #         it is out of sync with the underlying authentication mechanism.
    def dirty(self):
        return self.user.is_dirty()
    ##
    # Notify the CacheableAuthenticator that any extra references for user
    # creation can be freed.
    def minimize(self):
        if hasattr(self, '_CacheableAuthenticator__minimizable'):
            del self.__minimizable
            self._minimize()
        return
    ##
    # Called at instantiation time
    def _authenticate(self):
        raise ENotImplemented
    ##
    # Authenticate a user based on the information supplied in
    # the <code>keywords</dict> against an instance of a cached
    # user validation.
    # @note This method may need to 'reathenticate' based on
    #       external events.
    def _validate(self):
        raise ENotImplemented
    ##
    # Notify the CacheableAuthenticator that any extra references for user
    # creation can be freed.
    def _minimize(self):
        return
    def __cmp__(self, other):
        return cmp(self.current_key(self.keywords()),
                   other.current_key(other.keywords()))
    def __hash__(self):
        return hash(self.current_key(self.keywords()))
    def __str__(self):
        output = ('%s - User: %s, Current Key: %s' %
                  (self.__class__.__name__,self.user.name(),
                   self.current_key(**self.keywords())))
        return output
class PAMAuthenticator(CacheableAuthenticator):
    def current_id(klass, **keywords):
        return keywords['name']
    current_id = classmethod(current_id)
    def _authenticate(self):
        keywords = self.keywords()
        name = self.user.name()
        assert name == keywords['name'],("Internal inconsistancy, "
                                         "self.user.name() != "
                                         "keywords['name']")
        passwd = keywords['passwd']
        pamlib.validate(name, passwd)
        self.__passwd = passwd
    def _validate(self):
        keywords = self.keywords()
        if (keywords['name'] != self.user.name() or
            keywords['passwd'] != self.__passwd):
            raise EAuthenticationFailed()
class ClearTextAuthenticator(CacheableAuthenticator):
    def current_id(klass, **keywords):
        return keywords['name']
    current_id = classmethod(current_id)
    ##
    # @keyword 'name' The username to authenticate.
    # @keyword 'passwd' The clear text password of the user.
    def _authenticate(self):
        keywords = self.keywords()
        name = self.user.name()
        assert name == keywords['name'],("Internal inconsistancy, "
                                         "self.user.name() != "
                                         "keywords['name']")
        passwd = keywords['passwd']
        entry = self.user.shadow_entry()
        if not entry.password_matches_crypt(passwd):
            raise EAuthenticationFailed()
        self.__passwd = passwd
    ##
    # @keyword 'name' The username to validate.
    # @keyword 'passwd' The clear text password of the user.
    def _validate(self):
        keywords = self.keywords()
        if (keywords['name'] != self.user.name() or
            keywords['passwd'] != self.__passwd):
            raise EAuthenticationFailed()
class CryptAuthenticator(CacheableAuthenticator):
    def current_id(klass, **keywords):
        return keywords['name']
    current_id = classmethod(current_id)
    ##
    # @keyword 'name' The username to authenticate.
    # @keyword 'crypt' The clear text password of the user.
    def _authenticate(self, **keywords):
        keywords = self.keywords()
        name = self.user.name()
        assert name == keywords['name'],("Internal in consistancy, " 
                                         "self.user.name() != "
                                         "keywords['name']")
        crypt = keywords['crypt']
        entry = self.user.shadow_entry()
        if entry.crypt() != crypt:
            raise EAuthenticationFailed()
        self.__crypt = crypt
    ##
    # @keyword 'name' The username to validate.
    # @keyword 'crypt' The clear text password of the user.
    def _validate(self, **keywords):
        keywords = self.keywords()
        if (keywords['name'] != self.user.name() or 
            keywords['crypt'] != self.__crypt):
            raise EAuthenticationFailed()
from base64 import decodestring as _base64_decode
class BasicRFC2617Authenticator(CacheableAuthenticator):
    ##
    # @keyword 'credentials'  The base64 encoding of 
    #                         username:password.
    def current_id(klass, **keywords):
        return keywords['credentials']
    current_id = classmethod(current_id)
    def name(klass, **keywords):
        credentials = keywords['credentials']
        name, passwd = _base64_decode(credentials).split(':',1)
        return name
    name = classmethod(name)
    ##
    # @keyword 'name' The username to authenticate.
    # @keyword 'crypt' The clear text password of the user.
    def _authenticate(self):
        keywords = self.keywords()
        credentials = keywords['credentials']
        name,passwd = _base64_decode(credentials).split(':',1)
        assert name == self.user.name(),("Internal in consistancy, "
                                         "name != self.user.name()")
        entry = self.user.shadow_entry()
        if not entry.password_matches_crypt(passwd):
            raise EAuthenticationFailed()
        self.__credentials = credentials
    ##
    # @keyword 'name' The username to validate.
    # @keyword 'crypt' The clear text password of the user.
    def _validate(self):
        keywords = self.keywords()
        if keywords['credentials'] != self.__credentials:
            raise EAuthenticationFailed()
class DigestRFC2617Authenticator(CacheableAuthenticator):
    def __init__(self,user,**keywords):
        self.__next_nonce = None
        self._a1_base = None
        self._a1_base_hashed = 0
        CacheableAuthenticator.__init__(self,user,**keywords)
    ##
    # If the keywords has a nonce, return it.  Otherwise, use the keywords
    # to generate a new nonce and return it.
    #
    # @keyword nonce If there is a nonce value in here, return it.
    def current_id(klass,**keywords):
        return keywords['nonce']
    current_id = classmethod(current_id)
    def name(klass,**keywords):
        return keywords['username']
    name = classmethod(name)
    def next_id(self):
        return self.__next_nonce
    def initiate_nonce(self,nonce):
        if self.__next_nonce is not None:
            raise EInvalidValue('nonce',nonce,'Nonce value ' 
                                'has already been initialized.')
        self.__next_nonce = nonce
    def _authenticate(self):
        return
    ##
    # @keyword username  Username.
    # @keyword realm  The realm for which the user is being authenticated.
    # @keyword nonce  This value should match expected nonce value
    #                 which is stored in self._next_nonce.
    # @keyword cnonce  Optional nonce value from client for server auth.
    # @keyword method  The request method used.  Often used as part of digest.
    # @keyword uri  The uri requested.  Often used as part of digest.
    # @keyword algorithm  Optional param to specify algorithm.  Recognized are
    #                     MD5 and MD5-sess.  Default is MD5.
    # @keword qop  Optional quality of protection param.  Undefined goes with 
    #              lowest qualityy of protection.
    # @keyword body_hash Optional parameter.  MD5 hash of body may be used 
    #                    used in digest when qop is auth-int.
    # @keyword nc  Optional param, nonce count, showing number of times 
    #              this nonce has been authenticated.
    # @keyword nextnonce  Optional keyword describing next nonce.  It
    #                     is through this value that authenticator knows
    #                     what nonce to accept next.
    def _validate(self):
        keywords = self.keywords()
        if keywords['username'] != self.user.name():
            raise EAuthenticationFailed('Incorrect username')
        if keywords['nonce'] != self.__next_nonce:
            raise EAuthenticationFailed('Unexpected nonce value.')
        if keywords.has_key('nextnonce'):
            self.__next_nonce = keywords['nextnonce']
        A1 = self.security_data()
        A2 = self.message_data()
        digest = self.digest(A1,A2)
        if digest != keywords['response']:
            raise EAuthenticationFailed()
        return
    def security_data(self,**overrides):
        original = self.keywords()
        keywords = original.copy()
        keywords.update(overrides)
        hashed = 0
        if self._a1_base is not None and keywords['realm'] == original['realm']:
            A1_base = self._a1_base
        else:
            A1_base = '%s:%s:%s' % (self.user.name(),
                                    keywords['realm'],
                                    self.user.password())
        A1 = A1_base
        if keywords.has_key('algorithm'):
            if keywords['algorithm'] == 'MD5':
                pass
            elif keywords['algorithm'] == 'MD5-sess':
                hashed = 1
                A1_base = md5.new(A1_base).hexdigest()
                A1 = '%s:%s:%s' % (A1_base,keywords['nonce'],keywords['cnonce'])
            else:
                raise EInvalidValue('algorithm',keywords['algorithm'],
                                    'Algorithm must be blank, MD5, or MD5-sess')
        if not overrides:
            self._a1_base = A1_base
            self._a1_base_hashed = hashed
        return A1
    def message_data(self,**overrides):
        keywords = self.keywords().copy()
        keywords.update(overrides)
        A2 = '%s:%s' % (keywords['method'],keywords['uri'])
        if keywords.has_key('qop'):
            if keywords['qop'] == 'auth':
                pass
            elif keywords['qop'] == 'auth-int':
                if not keywords.has_key('body_hash'):
                    raise EInvalidValue('body_hash', None,'With qop == auth-int,'
                                        ' a body_hash value must be passed in.')
                A2 = '%s:%s' % (A2,keywords['body_hash'])
            else:
                raise EInvalidValue('qop',keywords['qop'],
                                    'QOP value not recognized.')
        return A2
    def digest(self,security_data,message_data,**overrides):
        keywords = self.keywords().copy()
        keywords.update(overrides)
        if keywords.has_key('qop'):
            digest = ('%s:%s:%s:%s:%s:%s' % 
                      (md5.new(security_data).hexdigest(),keywords['nonce'],
                       keywords['nc'],keywords['cnonce'],keywords['qop'],
                       md5.new(message_data).hexdigest()))
        else:
            digest = '%s:%s:%s' % (md5.new(security_data).hexdigest(),
                                   keywords['nonce'],
                                   md5.new(message_data).hexdigest())
        return md5.new(digest).hexdigest()
class UserManager(ServiceNode):
    class _NoneUser:
        def __init__(self):
            self.__name = 'NoneUser'
        def name(self):
            return self.__name
    def __init__(self):
        ##
        # Used to control access to the user control dictionaries.
        self.__lock = Lock()
        ##
        # There is only every one instance of a User cached in memory.
        self.__users = {'NoneUser':self._NoneUser()}
        ##
        # For every derived CacheableAuthenticator that has been used
        # to authenticate a User instance, there is one cached
        # authenticator instance.
        self.__pending = {DigestRFC2617Authenticator:[]}
        ServiceNode.__init__(self)
        return
    def has_user(self,name):
        users = self.__users
        if not users.has_key(name):
            try:
                user = User(name,0,PASSWD_FILE) 
                user._authenticators = {}
                users[name] = user
            except Exception:
                msglog.log("broadway", msglog.types.WARN, "User '%s' not found"%name)
                return False        
        return users.has_key(name)
    def get_user(self,name):
        users = self.__users
        if not users.has_key(name):
            user = User(name,0,PASSWD_FILE)
            user._authenticators = {}
            users[name] = user
        return users[name]
    def remove_user(self, name):
        users = self.__users
        if users.has_key(name):
            del users[name]
    def new_user(self,name):
        raise ENotImplemented(self.new_user)
    def initialize_authenticator(self,authenticator,**keywords):
        name = authenticator.name(**keywords)
        file = PASSWD_FILE
        if keywords.has_key('_file_'):
            file = keywords['_file_']
        users = self.__users
        self.__lock.acquire()
        try:
            if not users.has_key(name):
                try:
                    user = User(name,0,file)
                except EInvalidValue:
                    raise EAuthenticationFailed()
                user._authenticators = {}
                users[name] = user
                validator = authenticator(users[name],**keywords)
            else:
                user = users[name]
                current_key = authenticator.current_key(**keywords)
                validator = authenticator(user,**keywords)
            validator.validate(**keywords)
            next_key = validator.next_key()
            users[name]._authenticators[next_key] = validator
        finally:
            self.__lock.release()
        return validator
    def user_from_authenticator(self, authenticator, **keywords):
        validator = self.initialize_authenticator(authenticator,**keywords)
        return validator.user

    def user_from_pam(self, name, password, **keywords):
        return self.user_from_authenticator(PAMAuthenticator,name=name,
                                            passwd=password,**keywords)

    ##
    # Authenticate a user via the system user name and password.
    #
    # @param username The system username to authenticate.
    # @param password The clear text password of the user.
    # @return A User object representing the authenticated user.
    # @exception EAuthenticationFailed 
    def user_from_cleartext(self, name, password, **keywords):
        return self.user_from_authenticator(ClearTextAuthenticator,name=name,
                                            passwd=password,**keywords)
    def validator_from_cleartext(self,name,password,**keywords):
        return self.initialize_authenticator(ClearTextAuthenticator,name=name, 
                                             passwd=password,**keywords)
    ##
    # Authenticate a user via the system user name and already crypted
    # password.
    #
    # @param username The system username to authenticate.
    # @param password The password of the user, crypted.
    # @return A User object representing the authenticated user.
    # @exception EAuthenticationFailed 
    def user_from_crypt(self, name, crypted_password, **keywords):
        return self.user_from_authenticator(CryptAuthenticator,name=name,
                                            crypt=crypted_password,**keywords)
    def validator_from_crypt(self,name,crypted_password,**keywords):
        return self.initialize_authenticator(CryptAuthenticator,name=name,
                                             crypt=crypted_password,**keywords)
    ##
    #
    # @return A User object representing the authenticated user.
    # @exception EAuthenticationFailed 
    def user_from_rfc2617_basic(self, credentials, **keywords):
        return self.user_from_authenticator(BasicRFC2617Authenticator,
                                            credentials=credentials,**keywords)
    def validator_from_rfc2617_basic(self,credential,**keywords):
        return self.initialize_authenticator(BasicRFC2617Authenticator,
                                             credentials=credential,**keywords)
    def new_rfc2617_basic_user(self,**keywords):
        return self.__users['NoneUser']
    ##
    #
    # @return A User object representing the authenticated user.
    # @exception EAuthenticationFailed 
    def user_from_rfc2617_digest(self, **keywords):
        return self.validator_from_rfc2617_digest(**keywords).user
    def validator_from_rfc2617_digest(self,**keywords):
        authenticator = DigestRFC2617Authenticator
        file = PASSWD_FILE
        if keywords.has_key('_file_'):
            file = keywords['_file_']
        name = authenticator.name(**keywords)
        nonce = authenticator.current_id(**keywords)
        current_key = authenticator.current_key(**keywords)
        self.__lock.acquire()
        try:
            if not self.__users.has_key(name):
                user = User(name,0,file)
                user._authenticators = {}
            else:
                user = self.__users[name]
            authenticators = user._authenticators
            if not authenticators.has_key(current_key):
                pending = self.__pending[authenticator]
                if nonce in pending:
                    pending.remove(nonce)
                    authenticators[current_key] = authenticator(user,**keywords)
                    authenticators[current_key].initiate_nonce(nonce)
                else:
                    raise EAuthenticationFailed('Unknown nonce value.') 
            self.__users[name] = user
        finally:
            self.__lock.release()
        return self.initialize_authenticator(authenticator,**keywords)
    def new_rfc2617_digest_user(self,next_nonce):
        self.__pending[DigestRFC2617Authenticator].append(next_nonce)
        return self.__users['NoneUser']




