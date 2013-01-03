"""
Copyright (C) 2002 2004 2010 2011 Cisco Systems

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
# This module handles tasks related to the getting and setting of the MPX system date and time. 
##
import os
import os.path
import stat
import exceptions
import time
from mpx import properties as prpty

_ZONE_TARBALL     = 'zonefiles.tgz'
_ZONE_DIRECTORY   = prpty.TIMEZONE_DIR
_ZONE_INDEX       = 'zoneindex'
_ZONE_TMP_FILE    = os.path.join(prpty.TEMP_DIR, 'zonetmp')
_LOCAL_TIME_LINK  = os.path.join(prpty.ETC_DIR, 'localtime')
_DEBUG_LOG_FILE   = os.path.join(prpty.TEMP_DIR, 'mpxconfig.debug')
_TIME_CHANGED_FILE = os.path.join(prpty.ETC_DIR, 'mpx_timechanged.tmp')
_DIR_IGNORE_LIST  = [ os.path.join(_ZONE_DIRECTORY, 'Factory'),
                      os.path.join(_ZONE_DIRECTORY, 'SystemV'),
                      os.path.join(_ZONE_DIRECTORY, 'UCT'),
                      os.path.join(_ZONE_DIRECTORY, 'UTC'),
                      os.path.join(_ZONE_DIRECTORY, 'W-SU'),
                      os.path.join(_ZONE_DIRECTORY, 'iso3166.tab'),
                      os.path.join(_ZONE_DIRECTORY, 'posix'),
                      os.path.join(_ZONE_DIRECTORY, 'right'),
                      os.path.join(_ZONE_DIRECTORY, 'zone.tab'),
                      os.path.join(_ZONE_DIRECTORY, 'posixrules') ]
_TGZ_IGNORE_LIST  = [ 'Factory',
                      'iso3166.tab',
                      'posixrules',
                      'zone.tab' ]
_log = None
debug=0

##############################################################################
#
# class ESystemFailure
#
# Exception to report system command errors.
#
##############################################################################
class ESystemFailure( exceptions.Exception ):
    def __init__( self, cmd ):
        self.cmd = cmd
        
    def __str__( self ):
        return "Command failed: %s" % self.cmd


##############################################################################
#
# _get_tgz_file_name
#
# Function to get the name of the tar ball containing the time zone files.
#
# Returns:
#    The name of the file if it exists, None otherwise.
#
##############################################################################
def _get_tgz_file_name():
    tgz_filename = os.path.join( _ZONE_DIRECTORY, _ZONE_TARBALL )
    if os.path.isfile( tgz_filename ):
        return tgz_filename
    return None

 
##############################################################################
#
# _dir_visit
#
# 'Visit function' called by os.path.walk to traverse the directory containing
# the time zone information files.  Called once for each directory in the
# directory tree
#
# Input parameters:
#    dirname      - the name of the visited directory
#    names        - lists the files in the directory (gotten from
#                   os.listdir(dirname)). The visit function may modify names to
#                   influence the set of directories visited below dirname, e.g.,
#                   to avoid visiting certain parts of the tree. (The object
#                   referred to by names must be modified in place, using del
#                   or slice assignment.)
# Output parameters:
#    output_list  - list where results of the walk are stored
#
##############################################################################
def _dir_visit( output_list, dirname, names ):

    # Filter out names listed in _DIR_IGNORE_LIST.
    iName = 0
    while iName < len( names ):
        full_name = os.path.join( dirname, names[iName] )
        if full_name in _DIR_IGNORE_LIST:
            del names[iName]
        else:
            iName += 1

    # Add file names to ouput_list.  Path is relative to _ZONE_DIRECTORY
    reldir = ''
    if dirname != _ZONE_DIRECTORY:
        reldir = dirname.replace( _ZONE_DIRECTORY + '/', '', 1 )
    for n in names:
        # Skip directories.  The generated list only contains time zone files.
        if os.path.isfile( os.path.join( dirname, n ) ):
            output_list.append( os.path.join( reldir, n ) )


##############################################################################
#
# get_time_zones
#
# Function to get a list of the time zones supported by the system.
#
# Returns:
#    A sorted list of time zones.
#
##############################################################################
def get_time_zones():
    zlist = []
    
    # If the tarball exits, the use it, otherwise walk the directory.
    tgz_filename = _get_tgz_file_name()
    if tgz_filename:
        # Extract a listing from the tgz file
        p = os.popen( 'tar -tzf %s' % tgz_filename )
        list = p.readlines()
        p.close
        
        # Copy the list to the output, ignoring zero-length names, directories
        # (ending in '/'), and names listing in _TGZ_IGNORE_LIST.
        for raw_line in list:
            edited_line = raw_line.replace( './', '', 1 )[:-1]
            if not edited_line.endswith( '/' ) \
               and not edited_line in _TGZ_IGNORE_LIST \
               and len( edited_line ) > 0:
                zlist.append( edited_line )
    else:
        os.path.walk( _ZONE_DIRECTORY, _dir_visit, zlist )
        
    zlist.sort()
    return zlist


##############################################################################
#
# get_time
#
# Get the current system date and time.  This function is used instead of
# localtime() because it gets the REAL system time, bypassing translation
# based on the current processes' time zone.  Remember, the time zone may
# have been changed, so the process' time zone may no longer be valid.
#
# Returns:
#    A tuple of six integers and one string, as follows:
#    (month, day, year, hours, minutes, seconds, time-zone-abbreviation)
#
##############################################################################
def get_time():
    p = os.popen( 'date +%m/%d/%Y%n%T%n%Z' )
    date_result = p.readlines()
    p.close()
    
    assert( len( date_result ) == 3 )
    
    mdy  = date_result[0].split( '/' )
    hms  = date_result[1].split( ':' )
    zone = date_result[2][0:-1]
    
    return [int( mdy[0] ), int( mdy[1] ), int( mdy[2] ),
            int( hms[0] ), int( hms[1] ), int( hms[2] ),
            zone]

def log(msg): 
    if _log:
        _log.write('%s %s' % (time.ctime(),msg))

def create_log(debug):
    global _log
    if debug:
        _log = open(_DEBUG_LOG_FILE,'w')
        
        
##############################################################################
#
# set_time
#
# Set the system date, time, and time zone.  A log file is created in /tmp.
# The log file contains the function results, but it's primary purpose is to
# indicate, by it's very existance, that the system time has been changed.
# The file is deleted by rc.mpx during system initialization.
#
# Input parameters:
#   mmddyyyy - month/day/year tuple
#   hhmmss   - hours/minutes/seconds tuple
#   zone     - zone name, which is zone file name relative to the zone directory;
#              None if zone is not being changed.
#
# Exceptions raised:
#   ESystemError - os.system call failed
#   OSError      - another os call failed
#
##############################################################################
def set_time( mmddyyyy, hhmmss, zone ):
    
    # zlist - This contains the zone files that are present in _ZONE_DIRECTORY.
    #         zlist is used when the zonefiles.tgz is missing (which would 
    #         typically be in a platform like Laserbeak)
    zlist = []
    
    # Initiate the log file.
    p = os.popen( 'date' )
    log( "original date=%s" % p.readlines()[0] )
    p.close()

    # If a zone has been chosen to set, then use that. If no zone is chosen
    # by the user, then do nothing.
    if zone:
        
        # symlink_fn will store the zonefile for the selected zone
        symlink_fn = None
    
        # If zonefiles.tgz is present, then un-tar it to create zone files
        # and delete it later
        tgz_filename = _get_tgz_file_name()
        if tgz_filename:
            log('INFO: %s present. This is a legacy system. \n' % (tgz_filename))
            
            log('INFO: Creating zonefiles in %s. Un-tar %s \n' % (_ZONE_DIRECTORY, tgz_filename))
            cmd = 'tar -C %s -zxf %s' % (_ZONE_DIRECTORY, tgz_filename)
            result = os.system(cmd)
            log('<%s> returned %d\n' % (cmd, result))
            if result:
                raise ESystemFailure(cmd)

            log('INFO: Removing %s \n' % (tgz_filename))
            cmd = 'rm -rf %s' % (tgz_filename)
            result = os.system(cmd)
            log('<%s> returned %d\n' % (cmd, result))
            if result:
                raise ESystemFailure(cmd)

        # traverse the zone directory and display the available zone files
        os.path.walk( _ZONE_DIRECTORY, _dir_visit, zlist)
        if zlist.__contains__(zone):
            symlink_fn = os.path.join(_ZONE_DIRECTORY, zone)

        if symlink_fn is None:
            log('unable to update the time zone\n')
        else:
            # Remove existing symlink to the old time zone
            try:
                os.unlink( _LOCAL_TIME_LINK )
            except OSError, e:
                # OK if file does not exist
                if not e.errno == 2: raise

            # Add a symlink to the new time zone
            os.symlink(symlink_fn, _LOCAL_TIME_LINK)
            log('%s linked to %s\n' % (_LOCAL_TIME_LINK, symlink_fn))

    else:
        log('time zone not changed\n')

    # Set system date/time; date [-u|--utc|--universal] [MMDDhhmm[[CC]YY][.ss]]
    # os.system() returns 0 upon success.
    params = ( mmddyyyy[0], mmddyyyy[1], hhmmss[0], hhmmss[1], mmddyyyy[2], hhmmss[2] )
    date_cmd = 'date %02d%02d%02d%02d%4d.%02d' % params
    result = os.system( '%s 1>/dev/null 2>/dev/null' % date_cmd )
    log( '<%s> returned %d\n' % ( date_cmd, result ) )
    if result:
        raise ESystemFailure( date_cmd )
    
    # Set the hardware clock to the current system time.
    clock_cmd = 'hwclock --utc --systohc'
    result = os.system( '%s 1>/dev/null 2>/dev/null' % clock_cmd )
    log( '<%s> returned %d\n' % ( clock_cmd, result ) )
    if result:
        raise ESystemFailure( clock_cmd )
    
    # Log new date/time
    p = os.popen( 'date' )
    log( "new date=%s" % p.readlines()[0] )
    p.close()

    # Check whether 'UTC=yes" is commented in /etc/default/rcS or not
    # if not, update it when user configures time using mpxconfig
    if os.path.exists('/etc/default/rcS'):
        rcSupdated = False

        rcSh = open('/etc/default/rcS', 'r')
        rcSfile = rcSh.readlines()
        rcSh.close()

        newrcS = ''
        for line in rcSfile:
            if line.replace(' ', '').startswith('#UTC=yes'):
                newrcS += 'UTC=yes\n'
                rcSupdated = True
            else:
                newrcS += line

        if rcSupdated:
            rcSh = open('/etc/default/rcS', 'w')
            rcSh.write(newrcS)
            rcSh.close()


##############################################################################
#
# has_time_changed
#
# Tests if the system date or time has been modified by set_time().
#
# Returns:
#   0 - time has not changed
#   1 - time as changed
#
##############################################################################
def has_time_changed():
    return os.path.exists( _TIME_CHANGED_FILE )

if debug:
    _log = open(_DEBUG_LOG_FILE,'a')
        
##
# Test routine executed if this module is run as main.
##
if __name__ == "__main__":
    zones = get_time_zones()
    create_log(1)
    for z in zones:
        log( z + '\n' )
    print "%d lines written to zones.log" % len( zones )
    
