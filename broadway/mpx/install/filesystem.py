"""
Copyright (C) 2003 2006 2010 2011 Cisco Systems

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
# Helper functions that operate on files and directories.  Typically extended
# versions of functions in os, os.path, etc.
#
# @fixme Implement rm, cp, and ln.
# @fixme This probably belongs in MOAB. (moab.filesystem)

import os as _os
import types as _types
import glob as _glob
import errno as _errno

from moab.user.manager import PasswdFile as _PasswdFile
from moab.user.manager import GroupFile as _GroupFile

##
# Extends Python's os.makedirs() function with the following changes:
# <p>
# 1. The default mode is 0770, not 0777.
# 2. No error is raised if the directory already exists, or if it is a link to
#    a valid directory.
# 3. If any part of the path is a broken link, then the broken link is remove
#    before attempting to create the path.
# 4. It has a verbosity flag that defaults to writing the request to standard
#    out (for logging purposes).
# <p>
# Original os.makedirs() documentation: create a leaf directory and all
# intermediate ones. Works like mkdir, except that any intermediate path
# segment (not just the rightmost) will be created if it does not exist.  This
# is recursive.
#
# @param name The name of the leaf to create.
# @param mode The UNIX style file mode bit mask to use when creating a missing
#             directory (it does not effect the permissions of directories that
#             already exist.
# @default 0770
# @param verbosity Set level of diagnotstic messaging, 0 for no messages.
# @default 1 Output basic diagnostics.
def makedirs(name, mode=0770, verbosity=1):
    if verbosity:
        print "mpx.install.filesystem.makedirs(%r,mode=0%o)" % (name,mode)
    name = _os.path.normpath(name)
    if _os.path.isdir(name):
        # The directory (or a valid link to a directory) exists, that's fine.
        return
    if _os.path.exists(name):
        # A non-directory is in the way of the full path.
        # @note This could not be a broken link because os.path.exists()
        #       returns false for broken links.
        return
    # Check for broken links in the supplied path.
    pbl = name
    while not _os.path.exists(pbl):
        if _os.path.islink(pbl):
            if verbosity:
                print "    forced os.unlink(%r)" % (pbl,)
            _os.unlink(pbl)
            break
        dirname, basename = _os.path.split(pbl)
        if not dirname:
            # Scanned to the top of a relative path without finding a broken
            # link.
            break
        assert dirname != pbl, ("Reached a non-existent root %r." % dirname)
        assert basename, ("Appears that normalize failed.")
        pbl = dirname
    _os.makedirs(name, mode)
    return

##
# Extends Python's os.chown() function with the following changes:
# <p>
# 1. Supports user and group names as well as integers.
# 2. Supports optional file name glob, off by default.
# 3. Supports optional recursion, off by default.
# 4. Supports optional user name expansion in the path, off by default.
# 5. Supports optional expanion of environment variables in the path, off by
#    default. 
# 6. Supports optional ignoring of errors, off by default.
# 7. It has a verbosity flag that defaults to writing the request to standard
#    out (for logging purposes).
# @param path The path to chown.
# @param user The user name or uid to set as the owner.
# @param group The group name or gid to set as the group.
# @param glob If true (1), then the path is expanded using the standard UNIX
#             file expansion rules.
# @default 0
# @param recurse If true (1), then if path (or it's optionally globbed list) is
#                a directory, recurse into the directory, chown'ing all of its
#                entries (recusively).
# @default 0
# @param expandvars If true (1), then preform shell style environment expansion
#                   on the path.
# @default 0
# @param expanduser If true (1), then preform user name expansion on the path.
# @default 0
# @param ignore_errors If true (1), then ignore chown errors and continue
#                      processing the path.  If verbosity is not 0, then a
#                      message is output for each error, otherwise the error is
#                      silently ignored.
# @param verbosity If true (1), then a message is output to standard output
#                  describing the requested change in ownership.
# @default 1
# @param followslinks If true (1), and recurse is specified then symbolic
#                     links will be followed.  Otherwise (if 0), then
#                     any symbolic links encountered will not be followed
#                     even if recurse if specified.
# @default 1
# @param _verbosity Implementation specific flag, DO NOT USE.
# @param _uid Implementation specific flag, DO NOT USE.
# @param _gid Implementation specific flag, DO NOT USE.
# <p>
def chown(path, user, group, glob=0, recurse=0, expandvars=0,
          expanduser=0, ignore_errors=0, verbosity=1, followslinks=1,
          _verbosity=0,_gid=None,_uid=None):
    _verbosity = verbosity or _verbosity
    if verbosity:
        msg = "mpx.install.filesystem.chown(%r,%r,%r" % (path, user, group)
        if glob:
            msg += ",glob=1"
        if recurse:
            msg += ",recurse=1"
        if expandvars:
            msg += ",expandvars=1"
        if expanduser:
            msg += ",expanduser=1"
        if ignore_errors:
            msg += ",ignore_errors=1"
        if not followslinks:
            msg += ",followslinks=0"
        msg += ")"
        print msg

    # *************************************************************************
    # @fixme Work around for install code that specifies MPX_UID/MPX_GID.
    #        Those properties should be removed and all install scripts should
    #        use user/group names and ensure that the user manager has
    #        appropriate entries.
    # @fixme ^ clarification:  MPX_UID -> MPX_USR, MPX_GRP (or similiar) using
    #        names instead of numbers.  Since we (may) install in different
    #        environments, MPX_UID/MPX_GID should stay but be initialized by
    #        name.
    if _uid is None:
        try:
            _uid = int(user)
            user = _uid
        except:
            pass
    if _gid is None:
        try:
            _gid = int(group)
            group = _gid
        except:
            pass
    # @fixme End of work around.
    # *************************************************************************

    # @note user is _uid indicates that the user has already been validated and
    #       converted to a uid (this greatly accelerates recursion).
    uid = _uid
    if user is not _uid:
        user_entry = _as_entry(user, _PasswdFile)
        if user_entry is None:
            if ignore_errors:
                if _verbosity:
                    print "    ignoring missing user entry: %s" % user
                return
            raise OSError(_errno.ESRCH, "Invalid user: %r" % user)
        uid = user_entry.uid()
    # @note group is _gid indicates that the group has already been validated
    #       and converted to a gid (this greatly accelerates recursion).
    gid = _gid
    if group is not _gid:
        group_entry = _as_entry(group, _GroupFile)
        if group_entry is None:
            if ignore_errors:
                if _verbosity:
                    print "    ignoring missing group entry: %s" % group
                return
            raise OSError(_errno.ESRCH, "Invalid group: %r" % group)
        gid = group_entry.gid()
    if expandvars:
        path = _os.path.expandvars(path)
    if expanduser:
        path = _os.path.expanduser(path)
    files = (path,)
    if glob:
        files = _glob.glob(path)
    for file in files:
        try:
            _os.chown(file, uid, gid)
        except Exception, e:
            if ignore_errors:
                if _verbosity:
                    print "    ignoring error: %s" % e
            else:
                raise # We're not ignoring errors, re-raise the original
                      # exception.
        if recurse and _os.path.isdir(file):
            if followslinks or (not _os.path.islink(file)):
                chown(_os.path.join(file, '*'), uid, gid, glob=1, recurse=1,
                      ignore_errors=ignore_errors, verbosity=0,
                      followslinks=followslinks,
                      _verbosity=_verbosity,_uid=uid,_gid=gid)
    return

##
# Extends Python's os.chmod() function with the following changes:
# <p>
# 1. Supports optional file name glob, off by default.
# 2. Supports optional recursion, off by default.
# 3. Supports optional user name expansion in the path, off by default.
# 4. Supports optional expanion of environment variables in the path, off by
#    default. 
# 5. Supports optional ignoring of errors, off by default.
# 6. It has a verbosity flag that defaults to writing the request to standard
#    out (for logging purposes).
# @param path The path to chmod.
# @param mode The mode (in UNIX style bitmask) to apply to the file(s).
# @param dir  The mode (in UNIX style bitmask) to apply to the directories(s).
# @default The same permissions as mode, but the search (execute) bits follow
#          the read bits.
# @param glob If true (1), then the path is expanded using the standard UNIX
#             file expansion rules.
# @default 0
# @param recurse If true (1), then if path (or it's optionally globbed list) is
#                a directory, recurse into the directory, chmod'ing all of its
#                entries (recusively).
# @default 0
# @param expandvars If true (1), then preform shell style environment expansion
#                   on the path.
# @default 0
# @param expanduser If true (1), then preform user name expansion on the path.
# @default 0
# @param ignore_errors If true (1), then ignore chmod errors and continue
#                      processing the path.  If verbosity is not 0, then a
#                      message is output for each error, otherwise the error is
#                      silently ignored.
# @param verbosity If true (1), then a message is output to standard output
#                  describing the requested change in ownership.
# @default 1
# @param _verbosity Implementation specific flag, DO NOT USE.
# <p>
def chmod(path, mode, dir=None,glob=0, recurse=0, expandvars=0,
          expanduser=0, ignore_errors=0, verbosity=1,_verbosity=0):
    if dir is None:
        dir = (mode ^ 0111) # Turn off execute...
        if dir & 0400:
            dir |= 0100     # Turn back on search (execute) if readable.
        if dir & 0040:
            dir |= 0010
        if dir & 0004:
            dir |= 0001
    _verbosity = verbosity or _verbosity
    if verbosity:
        msg = "mpx.install.filesystem.chmod(%r,%r" % (path, mode)
        if glob:
            msg += ",glob=1"
        if recurse:
            msg += ",recurse=1"
        if expandvars:
            msg += ",expandvars=1"
        if expanduser:
            msg += ",expanduser=1"
        if ignore_errors:
            msg += ",ignore_errors=1"
        msg += ")"
        print msg
    if expandvars:
        path = _os.path.expandvars(path)
    if expanduser:
        path = _os.path.expanduser(path)
    files = (path,)
    if glob:
        files = _glob.glob(path)
    for file in files:
        try:
            if _os.path.isdir(file):
                _os.chmod(file, dir)
            else:
                _os.chmod(file, mode)
        except Exception, e:
            if ignore_errors:
                if _verbosity:
                    print "    ignoring error: %s" % e
            else:
                raise # We're not ignoring errors, re-raise the original
                      # exception.
        if recurse and _os.path.isdir(file):
            chmod(_os.path.join(file, '*'), mode, dir=dir, glob=1, recurse=1,
                  ignore_errors=ignore_errors, verbosity=0,
                  _verbosity=_verbosity)
    return

def _as_entry(id, klass):
    type_list = []
    type_list.extend(_types.StringTypes)
    type_list.extend((_types.IntType, _types.LongType))
    is_str    = ((1,) * len(_types.StringTypes)) + (0,) + (0,)
    assert type(id) in type_list, (
        "id must be an integer or string.")
    db = klass()
    db.load()
    if id not in db:
        return None
    return db[id]
