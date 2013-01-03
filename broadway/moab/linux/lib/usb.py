"""
Copyright (C) 2004 2010 2011 Cisco Systems

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
import re
import os
import exceptions

cur_debug_level = 5
prog_name = 'usb'

def logMsg(debug_level, msg):
    global cur_debug_level, prog_name
    
    if cur_debug_level >= debug_level:
        try:
            os.system('logger -t %s "%s"' % (prog_name, msg))
        except:
            print 'Could not log message via syslog: %s.' % msg
            
# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.            
def do_popen(cmd,reportoutput=0,reporterror=1):
    logMsg(5, 'Running command: %s.' % cmd)
    i,o,e = os.popen3(cmd)
    stderr = e.read()
    stdout = o.read()
    i.close()
    o.close()
    e.close()
    if reportoutput:
        logMsg(2, 'Got output of %s from cmd: %s.' % (stdout,
                                                      cmd))
    if reporterror:
        if len(stderr) != 0:
            logMsg(1, 'Got error of %s from cmd: %s.' % (stderr,
                                                         cmd))
    return (stdout, stderr)

# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.
def scanmounts():
    """creates dictionary from /proc/mounts"""
    # example: '/dev/sda1 /mnt/sda1 ext3 rw 0 0'
    #   device, mountpoint, type, options
    mounts = {}
    try:
        for line in open('/proc/mounts'):
            line = line.strip()
            if line[0:7] == '/dev/sd':
                tup = line.split(' ')
                device = tup[0]
                mountpoint = tup[1]
                fstype = tup[2]
                mtype = tup[3]
                opt1 = tup[4]
                opt2 = tup[5]
                mounts[device] = (mountpoint, fstype, mtype, opt1, opt2)
    except:
        logMsg(1, 'Got error reading/parsing /proc/mounts.')
    return mounts

## todo:  need to deal with case where patition table is non-existant.
##
## todo:  rewrite to use sfdisk

# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.
#
def getmap(device):
    """calls fdisk and returns a list of dictionaries containing the
    partition information.  device can be specified like 'sda' '/dev/sda'
    """
    if not device:
        return None

    pat = re.compile('.*(sd[a-z])')
    m = re.search(pat, device)
    if not m:
        return None
    dev = m.group(1)
    i,o,e = os.popen3('/sbin/fdisk -l /dev/%s' % dev)
    err = e.read().strip()
    no_part_table = "doesn't contain a valid partition table"
    if err.find(no_part_table) != -1:
        # Apparently no partition table was found.
        logMsg(1, "Couldn't find a partition table on USB device: %s" % dev)
        o.close()
        e.close()
        return []
    # Got an unrecognized error, just report it and bail.
    if err:
        raise Exception(err)
    out = o.readlines()
    o.close()
    e.close()

    parts = []
    if not out:
        return None

    # nice hairy regexp to grok this:
    # Device    Boot    Start       End    Blocks   Id  System
    # /dev/sda1   *         1       490     62719+  83  Linux
    # note: boot '*' may not be present, blocks may not have '+' or '-'
    #       to indicate that rounding has occured
    pat = re.compile(r'/dev/(sd[a-z]\d+)\s+(\*)?\s+(\d+)\s+(\d+)\s+(\d+)[\+\-]?\s+(\w+)\s+(.+)')
    for line in out:
        line = line.strip()
        m = re.search(pat, line)
        if m:
            dict =  { 'filesys' : m.group(1),
                      'boot'   : m.group(2),
                      'start'  : int(m.group(3)),
                      'end'    : int(m.group(4)),
                      'blocks' : int(m.group(5)),
                      'id'     : m.group(6),
                      'system' : m.group(7),
                      'dev'    : '/dev/%s' % m.group(1),
                      }
            parts.append(dict)
        else:
            pass
    return parts

# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.
#
def check_drive(scsi_dev):
    """Checks to see if the specified SCSI device (sda, sdb, etc.) is
still actually present by attempting to read a few bytes from it.
Returns 1 if it does appear to be present, and 0 otherwise.
"""
    # Test to see if this drive is actually there.
    # If it is really there, we should be able to read
    # a few bytes from it.  If it isn't we should
    # get an IO Error.
    devfile = '/dev/%s' % scsi_dev
    f = open(devfile, 'rb')
    didread = 0
    try:
        y = f.read(100)
        didread = 1
    except exceptions.IOError, e:
        didread = 0
    y = None
    f.close()   
    return didread

# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.
#
# Note: /proc/partitions is not very reliable!  It holds stale
#       information.  i.e. sometimes /dev/sda1 /dev/sda2 are no longer
#       active or sometimes they are available, but only show up as
#       /dev/sda.  However, doing an fdisk will update /proc/partitions.
#       Probably just better to run fdisk and parse it.
def scandrives(confirm=1):
    """Reads /proc/partitions and returns a list of SCSI devices
i.e. sda, sdb.  None if no matches.

Optional parameter confirm (default is 1): Set to 1 if you
want scandrives to confirm that the device is really there.
Set to 0 if you don't want it to confirm that.

Returns a list of drives.
"""
    drives = []
    
    pat = re.compile('\d+\s+\d+\s+\d+\s+(sd[a-z])\s+')
    for line in open('/proc/partitions'):
        line = line.strip()
        m = re.search(pat, line)
        if m:
            scsi_dev = m.group(1)
            if confirm:
                didread = check_drive(scsi_dev)
                if didread:
                    drives.append(scsi_dev)
            else:
                drives.append(scsi_dev)
    #
    return drives

# Note: At the moment, this routine is duplicated in broadway/moab/linux/bin/hotplug.
#       If you are updating it here, please update it there too.
#
def grabpartitions(dev_list):
    """Takes a list of devices (e.g. sda, sdb) and 
    Returns a list of partition dictionaries (or None).
    """
    partitions = []
    
    for drive in dev_list:
        fparts = getmap(drive)
        if fparts:
            for p in fparts:
                partitions.append(p)
    #
    return partitions

# Note: This should probably be elsewhere
def prompt_yn(prmpt, enb_cancel = 0):
    """Prompt user with a yes/no question."""
    invalid = 1
    prompt = "%s (y/n)? " % prmpt
    if enb_cancel:
        prompt += "or type 'Control-C' to cancel "
    while(1):
        try:
            c = raw_input(prompt)
            print "\n"
        except KeyboardInterrupt:
            if enb_cancel:
                return None
            else:
                continue
        c = c.strip()
        c = c.lower()
        if c == 'y':
            return 1
        elif c == 'n':
            return 0
