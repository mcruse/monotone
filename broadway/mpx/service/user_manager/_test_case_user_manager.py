"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
from mpx_test import DefaultTestFixture, main

import os
import md5
from crypt import crypt as __crypt
def _crypt(password):
    return __crypt(password,'xx')

from base64 import encodestring as __base64_encode
def _base64_encode(name, password):
    return __base64_encode("%s:%s" % (name, password))[:-1] # Rm \n

from base64 import decodestring as __base64_decode
def _base64_decode(encodedstring):
    return __base64_decode(encodedstring).split(":",1)

import mpx.lib # Bootstraping...
from mpx.lib.uuid import UUID
from mpx.lib.exceptions import ENotImplemented
from moab.user.manager import PasswdFile, PasswdEntry
from _manager import User
from _manager import UserManager
from _manager import ClearTextAuthenticator
from _manager import CryptAuthenticator
from _manager import BasicRFC2617Authenticator
from _manager import DigestRFC2617Authenticator
from _manager import EAuthenticationFailed

class TestCase(DefaultTestFixture):
    _tmp_index = 0
    _tmp_id = 1812
    NAME_PASSWD_MAP = {
        'test':'test',
        'two':'number2',
        }
    def setUp(self):
        DefaultTestFixture.setUp(self)
        self.user_manager = mpx.lib.factory(
            'mpx.service.user_manager.UserManager'
            )
        self.user_manager.configure({'name':'User Manager','parent':None})
        self.passwd_file = self.new_passwd_file()
        f = open(self.passwd_file,'r')
        return
    def tearDown(self):
        self.user_manager.stop()
        self.user_manager = None
        os.unlink(self.passwd_file)
        self.passwd_file = None
        DefaultTestFixture.tearDown(self)
        return
    def user_clear_text_credentials(self, name):
        return self.NAME_PASSWD_MAP[name]
    def user_crypt_credentials(self, name):
        return _crypt(self.user_clear_text_credentials(name))
    def user_base64_credentials(self, name):
        return _base64_encode(name, self.user_clear_text_credentials(name))
    def add_pf_user(self, pf, name):
        pe = PasswdEntry()
        pe.user(name)
        pe.crypt(self.user_crypt_credentials(name))
        pe.uid(TestCase._tmp_id)
        pe.gid(TestCase._tmp_id*10)
        TestCase._tmp_id += 1
        pe.directory(os.path.join(os.environ['TMP_DIR'],name))
        pe.shell('/bin/sh')
        pf[pe.user()] = pe
        return
    def new_passwd_file(self):
        if not os.environ.has_key('TMP_DIR'):
            os.environ['TMP_DIR'] = '/tmp'
        name = os.path.join(os.environ['TMP_DIR'], 'passwd')
        self.__class__._tmp_index += 1
        pf = PasswdFile(name)
        for user in self.NAME_PASSWD_MAP.keys():
            self.add_pf_user(pf, user)
        pf.save()
        return name
    #
    # Underlying CacheableAuthenticator instantiations.
    #
    def test_new_ClearTextAuthenticator(self, name='test'):
        passwd = self.user_clear_text_credentials(name)
        ua = ClearTextAuthenticator(User(name,0,self.passwd_file),
                                    name=name,passwd=passwd)
        return
    def test_new_CryptAuthenticator(self, name='test'):
        crypt = self.user_crypt_credentials(name)
        ua = CryptAuthenticator(User(name,0,self.passwd_file),
                                name=name,crypt=crypt)
        return
    def test_new_BasicRFC2617Authenticator(self, name='test'):
        credentials = self.user_base64_credentials(name)
        ua = BasicRFC2617Authenticator(User(name,0,self.passwd_file),
                                       name=name,credentials=credentials)
        return
    def test_new_DigestRFC2617Authenticator(self):
        nonce = UUID()
        none_user = self.user_manager.new_rfc2617_digest_user(nonce)
        assert none_user.name() == 'NoneUser','Returned wrong user'
    ##
    # For each Underlying CacheableAuthenticator instantiation, use the
    # UserManager's user_from_authenticator() method.
    #
    def test_user_from_authenticator(self, name='test'):
        user = self.user_manager.user_from_authenticator(
            ClearTextAuthenticator,
            name=name,
            passwd=self.user_clear_text_credentials(name),
            _file_=self.passwd_file
            )
        user = self.user_manager.user_from_authenticator(
            CryptAuthenticator,
            name=name,
            crypt=self.user_crypt_credentials(name),
            _file_=self.passwd_file
            )
        user = self.user_manager.user_from_authenticator(
            BasicRFC2617Authenticator,
            credentials=self.user_base64_credentials(name),
            _file_=self.passwd_file
            )
        try:
            user = self.user_manager.user_from_authenticator(
                DigestRFC2617Authenticator,
                _file_=self.passwd_file,username=name,nonce=None)
        except:
            pass
        return
    #
    # Use each of the UserManager's convenience user_from_* methods.
    #
    def test_user_from_cleartext(self, name='test', password=None):
        if password is None:
            password=self.user_clear_text_credentials(name)
        user = self.user_manager.user_from_cleartext(name, password,
                                                     _file_=self.passwd_file)
        return
    def test_user_from_crypt(self, name='test'):
        user = self.user_manager.user_from_crypt(
            name,
            self.user_crypt_credentials(name),
            _file_=self.passwd_file
            )
        return
    def test_user_from_rfc2617_basic(self, name='test'):
        user = self.user_manager.user_from_rfc2617_basic(
            self.user_base64_credentials(name),
            _file_=self.passwd_file
            )
        return
    def test_user_from_rfc2617_digest(self, name='test'):
        try:
            self._test_user_from_rfc2617_digest(name)
        except ENotImplemented:
            pass
        else:
            self.fail('Digest authentication should raise ENotImplemented')
    def _test_user_from_rfc2617_digest(self, name='test'):
        nonce = UUID()
        next_nonce = UUID()
        realm = 'digest test'
        algorithm = 'MD5'
        method = 'GET'
        uri = '/index.html'
        password = self.NAME_PASSWD_MAP[name]
        A1 = '%s:%s:%s' % (name,realm,password)
        A2 = '%s:%s' % (method,uri)
        digest = '%s:%s:%s' % (md5.new(A1).hexdigest(),nonce,
                               md5.new(A2).hexdigest())
        digest = md5.new(digest).hexdigest()
        none_user = self.user_manager.new_rfc2617_digest_user(nonce)
        assert none_user.name() == 'NoneUser','New digest returned wrong user'
        user = self.user_manager.user_from_rfc2617_digest(
            _file_=self.passwd_file,username=name,nonce=nonce,
            nextnonce=next_nonce,realm=realm,
            algorithm=algorithm,method=method,uri=uri,response=digest)
        nonce = next_nonce
        next_nonce = UUID()
        method = 'POST'
        uri = '/post.html'
        A2 = '%s:%s' % (method,uri)
        digest = '%s:%s:%s' % (md5.new(A1).hexdigest(),nonce,
                               md5.new(A2).hexdigest())
        digest = md5.new(digest).hexdigest()
        user = self.user_manager.user_from_rfc2617_digest(
            _file_=self.passwd_file,username=name,nonce=nonce,
            nextnonce=next_nonce,realm=realm,
            algorithm=algorithm,method=method,uri=uri,response=digest)
        assert user.name() == name,'Wrong user returned.'
    def user_manager_internal_state(self):
        class State:
            def __init__(self, user_manager):
                self.cached_users = user_manager._UserManager__users
                return
            def __str__(self):
                return ("""State:
                    cached_users: %r
                    cached_authenticators: %r
                    cached_groups: %r""" % 
                        (self.cached_users, self.cached_authenticators,
                         self.cached_groups))
            def assert_caches_empty(self):
                self.assert_user_cache_empty()
            def assert_user_cache_empty(self):
                assert len(self.cached_users) == 1, 'User cache not empty.'
            def assert_authenticator_cache_empty(self):
                message = 'User %s has cached authenticator.'
                for user in self.cached_users.values():
                    assert len(user._authenticators.keys()) == 0, message % user
            def assert_user_cache_length(self, length):
                length += 1
                cached = self.cached_users
                assert len(cached) == length,('User cach should '
                                              'have %d, not %d' % 
                                              (length,len(cached)))
                if len(self.cached_users) != length:
                    raise"User cache should have %d entries, not %d." % (
                        length, len(self.cached_users))
                return
            def assert_authenticator_cache_length(self, length):
                count = 0
                for user in self.cached_users.values():
                    if hasattr(user,'_authenticators'):
                        count += len(user._authenticators.keys())
                assert count == length,("Authenticator cache should should have"
                                        " %d entries, not %d." % (length,count))
            def assert_user_instance(self, name, instance):
                assert self.cached_users[name] is instance, 'User changed.'
            def assert_authenticator_instance(self, name, key, instance):
                if self.cached_users[name]._authenticators[key] is not instance:
                    raise "Cached authenticator instance changed."
                return
            def assert_not_authenticator_instance(self, name, key, instance):
                try:
                    self.assert_authenticator_cache_empty()
                except AssertionError:
                    pass
                else:
                    raise AssertionError('Cached authenticator not changed.')
        return State(self.user_manager)
    ##
    # Verify that caching is working.
    def test_caching_implementation(self):
        #
        # Confirm that initally all caches are empty.
        #
        state = self.user_manager_internal_state()
        state.assert_caches_empty()
        #
        # Confirm that after authenticating the first user, that the
        # User Cache and Authenticator Cache have exaclty one entry.
        #
        # Adds one authenticator to User('test')
        self.test_user_from_cleartext()
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(1)
        state.assert_authenticator_cache_length(1)
        test_user = state.cached_users['test']
        test_clear_text_authenticator = (
            test_user._authenticators['ClearTextAuthenticator:test']
            )
        state = None
        #
        # Confirm that after 'reauthenticating' the first user, that the
        # User Cache and Authenticator Cache have exaclty one user and
        # that it is unchanged.
        #
        # Uses cached authenticator from above.
        self.test_user_from_cleartext()
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(1)
        state.assert_authenticator_cache_length(1)
        state.assert_user_instance('test', test_user)
        state.assert_authenticator_instance('test',
                                            'ClearTextAuthenticator:test',
                                            test_clear_text_authenticator)
        state = None
        #
        # Confirm that after authenticating the test user with the remaining
        # standard authenticators that there is still only one cached user
        # and that it is the original instance.
        # Adds one authenticator to cache
        self.test_user_from_crypt()
        # Adds one authenticator to cache
        self.test_user_from_rfc2617_basic()
        # Adds one authenticator to cache
        self.test_user_from_rfc2617_digest()
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(1)
        # Since digest does not work this is 3, will be 4.
        state.assert_authenticator_cache_length(3)
        state.assert_user_instance('test', test_user)
        state.assert_authenticator_instance('test',
                                            'ClearTextAuthenticator:test',
                                            test_clear_text_authenticator)
        test_crypt_authenticator = (
            test_user._authenticators['CryptAuthenticator:test'])
        state.assert_not_authenticator_instance('test',
                                                'ClearTextAuthenticator:test',
                                                test_crypt_authenticator)
        test_basic_authenticator = (
            test_user._authenticators['BasicRFC2617Authenticator:dGVzdDp0ZXN0'])
        state = None
        #
        # Confirm that after reauthenticating the test user with all
        # autenticators that there has been no change of state.
        #
        self.test_user_from_cleartext()
        self.test_user_from_crypt()
        self.test_user_from_rfc2617_basic()
        # Omitting digest authenticator because it will cause
        #   additional authenticator to be added to cache.
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(1)
        state.assert_authenticator_cache_length(3)
        state.assert_user_instance('test', test_user)
        state.assert_authenticator_instance('test',
                                            'ClearTextAuthenticator:test',
                                            test_clear_text_authenticator)
        state.assert_authenticator_instance('test','CryptAuthenticator:test',
                                            test_crypt_authenticator)
        state.assert_authenticator_instance('test',
                                            'BasicRFC2617Authe'
                                            'nticator:dGVzdDp0ZXN0',
                                            test_basic_authenticator)
        state = None
        #
        # Validate the cache states after authenticating a different user
        # ('two').
        #
        # Adds one authenticator to cache.
        self.test_user_from_cleartext('two')
        # Adds one authenticator to cache.
        self.test_user_from_crypt('two')
        # Adds one authenticator to cache.
        self.test_user_from_rfc2617_basic('two')
        # Adds one authenticator to cache.
        self.test_user_from_rfc2617_digest('two')
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(2) # 'test', 'two'
        # 6 instead of 8 because digest auths are not complete.
        state.assert_authenticator_cache_length(6)
        state.assert_user_instance('test', test_user)
        state.assert_authenticator_instance('test',
                                            'ClearTextAuthenticator:test',
                                            test_clear_text_authenticator)
        state.assert_authenticator_instance('test',
                                            'CryptAuthenticator:test',
                                            test_crypt_authenticator)
        state.assert_authenticator_instance('test',
                                            'BasicRFC2617Authenticator:'
                                            'dGVzdDp0ZXN0',
                                            test_basic_authenticator)
        two_user = state.cached_users['two']
        two_clear_text_authenticator = (
            two_user._authenticators['ClearTextAuthenticator:two'])
        two_crypt_authenticator = (
            two_user._authenticators['CryptAuthenticator:two'])
        two_basic_authenticator = (
            two_user._authenticators['BasicRFC2617Authenticator:dHdvOm51bWJlcjI='])
        #
        # Validate the cache states after reauthenticating user ('two').
        #
        self.test_user_from_cleartext('two')
        self.test_user_from_crypt('two')
        self.test_user_from_rfc2617_basic('two')
        # Omitting digest call because it will add another 
        #   authenticator to cache.
        state = self.user_manager_internal_state()
        state.assert_user_cache_length(2) # 'test', 'two'
        # 6 instead of 8 because digest auths are not complete.
        state.assert_authenticator_cache_length(6)
        state.assert_user_instance('test', test_user)
        state.assert_user_instance('two', two_user)
        state.assert_authenticator_instance('test',
                                            'ClearTextAuthenticator:test',
                                            test_clear_text_authenticator)
        state.assert_authenticator_instance('test',
                                            'CryptAuthenticator:test',
                                            test_crypt_authenticator)
        state.assert_authenticator_instance(
            'test','BasicRFC2617Authenticator:dGVzdDp0ZXN0',
            test_basic_authenticator)
        state.assert_authenticator_instance('two',
                                            'ClearTextAuthenticator:two',
                                            two_clear_text_authenticator)
        state.assert_authenticator_instance('two',
                                            'CryptAuthenticator:two',
                                            two_crypt_authenticator)
        state.assert_authenticator_instance(
            'two','BasicRFC2617Authenticator:dHdvOm51bWJlcjI=',
            two_basic_authenticator)
        state = None
        #
        # Validate that when a cached authenticator is marked dirty that,
        # it is removed.
        #
        # Cause the authentication file to have it's save could incremented.
        pf = PasswdFile(self.passwd_file)
        self.NAME_PASSWD_MAP['dirty'] = 'mind'
        self.add_pf_user(pf, 'dirty')
        pf.save()
        # Attempt to authenticate with an invalid password.  The dirty
        # cache entry should be removed.  Since the authenticate fails,
        # there will be no new clear text cached authenticator.
        try:
            self.test_user_from_cleartext('test', 'remove_auth')
        except:
            # @todo Not sure what is wrong here,
            #       but except EAuthenticationFailed does not
            #       except EAuthenticationFailed...dang!!!
            pass
        state = self.user_manager_internal_state()
        # This is 5 instead of 7 because digest auths are not complete.
        state.assert_authenticator_cache_length(5)
        state = None
        state = None
        # @todo Update self.pass_file and ensure that the chaches are empty.
        state = None
        # @todo Ensure new authentication tokens work, and that the old
        #       ones don't.
        state = None
        return
#
# Support a standalone excecution.
#
if __name__ == '__main__':
    main()
