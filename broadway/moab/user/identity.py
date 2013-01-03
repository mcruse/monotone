"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
# @todo Support mapping x509.v3 cerificates...

from array import array as _array
from random import randint as _randint
from string import join as _join
from time import time as _now
from md5 import new as _MD5
from crypt import crypt as _crypt

from manager import ShadowFile as _ShadowFile
from manager import SHADOW_FILE as _SHADOW_FILE
from manager import GROUP_FILE as _GROUP_FILE
from moab.lib.crc import crc16 as _crc16

from mpx import properties

# @warning DO NOT CHANGE THIS LIST.  It is defined by the UNIX crypt
#          standard!
_saltchars = ('abcdefghijklmnopqrstuvwxyz' +
              'ABCDEFGHIJKLMNOPQRSTUVWXYZ' +
              '01234567890./')

##
# This represents the Broadway user/password salt calculation.  This salt is
# used to encrypt the username (which is sent crypt sans salt) and the
# password (which is used in the creation of the MD5 signature).
#
# I will use the crypted username and scan the user database for a username
# that matches using it's passwd's salt.  Then the username, passwd and
# orignal seed can be used to calculate a comparison signature.
#
# @note
# Calculating the salt with the username and password helps protect against
# dictionary based attacks, UNLESS THE USER NAME IS KNOWN.  Therefore, to
# maximize security, systems should not keep pre-defined usernames.
def sulfur_for(username, password,
               calculate=1, file=_SHADOW_FILE):
    if calculate:
        text = _join(username, password)
        crc = _crc16(text)
        b1 = _saltchars[(crc >> 8) % 64]
        b2 = _saltchars[(crc & 0xff) % 64]
        return "%s%s" % (b1, b2)
    shadow_file = _ShadowFile(file)
    shadow_file.load()
    shadow = shadow_file[username]
    return shadow.crypt()[3:5]

def crypted(username, password, word,
            sulfur=None, calculate=1, file=_SHADOW_FILE):
    if sulfur is None:
        sulfur = sulfur_for(username, password, calculate, file)
    return _crypt(word, sulfur)

def crypted_password(username, password,
                     sulfur=None, calculate=1, file=_SHADOW_FILE):
    salt = crypted(username, password, password, 
                   sulfur, calculate, file)
    crypted_pwd = crypted(username, password, password, 
                          sulfur='$1$' + salt + '$')
    return crypted_pwd

def crypted_username(username, password,
                     sulfur=None, calculate=1, file=_SHADOW_FILE):
    return crypted(username, password, username,
                   sulfur, calculate, file)

def sulfurfree(crypted_word):
    return crypted_word[2:]

def level1_signature_for(seed, username, password=None,
                         sulfur=None, calculate=1, file=_SHADOW_FILE):
    # LEVEL 1 is a LEVEL to signature that does not include the message
    # in the MD5 calculation.
    return level2_signature_for('', seed, username, password,
                                sulfur, calculate, file)

def level2_signature_for(message, seed, username, password=None,
                         sulfur=None, calculate=1, file=_SHADOW_FILE):
    # Get sulfur based on arguments...
    if sulfur is None:
        if password is None:
            sulfur = sulfur_for(username, password, 0, file)
        else:
            sulfur = sulfur_for(username, password, 1, file)
    elif len(sulfur) != 2:
        raise EInvalidValue('sulfur must be None or a two character string.')
    # Calculate the crypted, sulfurfree password based on the arguments...
    sf_pass = None
    if password is None:
        passwd = _ShadowFile(file)
        passwd.load()
        entry = passwd[username]
        sf_user = sulfurfree(entry.crypt())
    else:
        sf_pass = sulfurfree(crypted_password(username, password,
                                              sulfur, calculate, file))
    # Calculate the crypted, sulfurfree username based on the arguments...
    sf_user = sulfurfree(crypted_username(username, password,
                                          sulfur, calculate, file))
    md5 = _MD5(sf_pass)
    md5.update(seed)
    md5.update(message)
    return _join(sf_user, md5.hexdigest().lower())

##
# Compare a supplied LEVEL 1 signature with a correctly calculated version.
def level1_validate(signature, seed, user, password=None,
                    sulfur=None, calculate=1, file=_SHADOW_FILE):
    validate_sig = level1_signature_for(seed, user, password,
                                        sulfur, calculate, file)
    return signature == validate_sig

##
# Compare a supplied LEVEL 2 signature with a correctly calculated version.
def level2_validate(signature, message, seed, user, password=None,
                    sulfur=None, calculate=1, file=_SHADOW_FILE):
    validate_sig = level2_signature_for(message, seed, user, password,
                                        sulfur, calculate, file)
    return signature == validate_sig

##
# Generate a random, time-based, hopefully unique, seed.
def new_seed():
    result = _array('c',str(_now()))
    for i in range(0,_randint(10,20)):
        result.append(chr(_randint(0,255)))
    return _MD5(result.tostring()).hexdigest().lower()

##
# Allows higher layers or applications to easily add an extra "session" or
# "identity" token/validation.
def context_seed(seed, context):
    return _MD5(_join(seed, context)).hexdigest().lower()

##
# Provides support for the original Config Service Security Key.
def csiked_password(password):
    return _crypt(password, "en")
