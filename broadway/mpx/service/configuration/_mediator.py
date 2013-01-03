"""
Copyright (C) 2001 2002 2003 2010 2011 Cisco Systems

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
import md5
import urllib
import array
from random import randrange
import urllib2
import mpx.lib

from mpx.service import ServiceNode
from mpx.lib import msglog, threading, pause, BinaryString
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, parse_xml
from mpx.lib.exceptions import EInvalidValue, EInvalidXML, EUnknownVersion, EFileNotFound
from mpx.lib.exceptions import ENotImplemented, MpxException
from mpx.lib.node import as_node
from _const import SOFT_EXIT, HARD_EXIT
from mpx import properties

##
# @todo A bit blunt at the moment.  It should be integrated with
#       mpx.system.run()
def soft_exit():
    msglog.log('broadway',msglog.types.INFO, "Soft Exit!");
    os._exit(0)

def hard_exit():
    msglog.log('broadway',msglog.types.INFO, "Hard Exit!");
    msglog.log('broadway',msglog.types.INFO, "Rebooting ...");                                                       
    try:
        os.system('sync')
        os.system('sync')
        os.system('reboot -f')            
            
    except Exception, e:
        raise Exception('Could not reboot system [%s]' % str(e))

    os._exit(-1) # Can't get here...

exit_map = {
    SOFT_EXIT:soft_exit,
    HARD_EXIT:hard_exit
    }

def _exit(flag):
    try:
        exit_function = exit_map[flag]
    except:
        raise EInvalidValue, ('flag',flag)
    schedule(exit_function)

def schedule(function,seconds=5):
    def wait_and_do(seconds,function):
        pause(seconds)
        function()
    schedule_thread = threading.Thread(target=wait_and_do,args=(seconds,function))
    schedule_thread.start()

##
# This class implements the configuration service.  In the terminology of the
# Broadway architecture it is known as the configuration service's
# <i>mediator</i>.
# <p>This class is never directly instantiated.  It is instantiated via the
# configuration service's factory, during Broadway's initialization.  The
# primary reason that this class is documented is to describe its
# configuration method.</p>
class Service(ServiceNode):
    ##
    # This class variable is used in introspective configuration
    # creation.
    __module__ = "mpx.service.configuration"
    BROADWAY_ROOT =     properties.ROOT 
    VERSION_FILE =      properties.VERSION_FILE
    NODEDEF_DBFILE =    properties.NODEDEF_DBFILE
    NODEDEF_DBFILE_EN = properties.NODEDEF_DBFILE_EN
    NODEDEF_ZIPFILE =   properties.NODEDEF_ZIPFILE
    NODEDEF_MD5FILE =   properties.NODEDEF_MD5FILE
    NONE = 'NONE'
    ZIP = 'ZIP'

    def __init__(self):
        ServiceNode.__init__(self)
    ##
    # Configures the Configure SubService.
    #
    # @param config  Dictionary holding configuration.
    #              the node.
    # @key name  The name of this node.
    # @required
    # @key parent  The url of the parent of this node.
    # @required
    # @key enabled  Enable service.  This allows
    #               services to be instanciated on
    #               the system but not enabled.  This
    #               is conveniant for services that should
    #               only be accessed at certain times, but disabled
    #               the rest of the time.
    # @value 0;1
    # @default 1
    # @key debug  Run service in debug mode.  Some services
    #             give additional output if they are running in
    #             debug mode.
    # @value 0;1
    # @default 0
    #
    # @note If this node has a parent, then this node will
    #       add itself a child to that parent.
    #
    def configure(self, config):
        ServiceNode.configure(self, config)
    ##
    # @return Configuration dictionary.
    #
    def configuration(self):
        config = ServiceNode.configuration(self)
        return config
    ##
    # Start the Configure service.
    #
    def start(self):
        ServiceNode.start(self)
            
    ##
    # Stop the Configure service.
    #
    def stop(self):
        ServiceNode.stop(self)
    ##
    # @returns The contents of the Broadway XML configuration file as a string.
    def read(self):
        f = open(properties.CONFIGURATION_FILE)
        try:
            response = f.read()
        finally:
            f.close()
        return response

    ##
    # @returns The XML representation of the running system as a string.
    def read_runtime(self):
        return mpx.lib.configure.build_xml('/')

    ##
    # @returns The XML representation of the running system as a string.
    #invoke with /nodebrowser/services/network/rna/configuration?action=invoke&method=save_runtime
    def save_runtime(self):
        return mpx.lib.configure.save_xml('/')

    def configuration_version(self):
        root = as_node('/')
        config = root.configuration()
        if config.has_key('node_def_version'):
            return config['node_def_version']
        raise EUnknownVersion

    def broadway_version(self):
        
        ## Force use of legacy protocol
        ## return "0.0.0"
    
        f = None
        try:
            f = open(os.path.join(self.BROADWAY_ROOT, self.VERSION_FILE))
            v = f.readline()[:-1]
            if not v:
                raise EUnknownVersion
            f.close()
            return v
        except IOError:
            if f: f.close()
            raise EUnknownVersion

    def get_version(self):
        msglog.log('broadway',msglog.types.WARN,
                   'Invokation of deprecated ' +
                   '/services/configuration.get_version() API.')
        return self.broadway_version()

    def _copy_encoded(self,source_file,target_name):
        source = source_file
        
        target = open(target_name, 'w+')
        h = source.read(4096)
        while h:
            target.write(urllib.quote(h))
            h = source.read(4096)
        target.close()
        return

    ##
    # @returns A string that represents the nodedef DB.
    def read_nodedef_db(self,compression_algorithm=NONE):
        f = None
        try:
            if compression_algorithm == self.NONE:
                try:
                    f = open(os.path.join(self.BROADWAY_ROOT,
                                          self.NODEDEF_DBFILE_EN))
                except IOError:
                    f = self._open_nodedef_db()
                    self._copy_encoded(f, os.path.join(self.BROADWAY_ROOT,
                                                       self.NODEDEF_DBFILE_EN))
                    
                    f.close()
                    f = None
                    f = open(os.path.join(self.BROADWAY_ROOT,
                                          self.NODEDEF_DBFILE_EN))
            elif compression_algorithm == self.ZIP:
                f = open(os.path.join(self.BROADWAY_ROOT, self.NODEDEF_ZIPFILE))
            else:
                raise EInvalidValue('compression_algorithm',
                                    compression_algorithm)
            return BinaryString(f.read())
        except IOError, ie:
            if f: f.close()
            raise MpxException('Could not read nodedef database: %s' % str(e))

    ##
    # Replace the MPX's current nodedef DB with <i>db</i>.
    # @param db A string that represents the nodedef DB.
    def write_nodedef_db(self, db):
        raise ENotImplemented

    ##
    # @returns A string that is the MD5 checksum of the nodedef DB.
    def get_nodedef_md5(self):
        f = None
        try:
            f = open(os.path.join(self.BROADWAY_ROOT, self.NODEDEF_MD5FILE))
            t = f.readline().split()[0]
            f.close()
            f = None
            if len(t) != 32: raise Exception('Invalid MD5.')
            return t
        except:
            if f: f.close()
        f = None
        try:
            n = md5.new()
            f = self._open_nodedef_db()
            for l in f.xreadlines():
                n.update(l)
            f.close()
            
   
            try:
                f = open(os.path.join(self.BROADWAY_ROOT, self.NODEDEF_MD5FILE),
                         'w+')
                f.write(n.hexdigest())
                f.write('  %s\n' % self.NODEDEF_DBFILE)
                f.close()
            except:
                if f: f.close()
            f = None
            return n.hexdigest()
        except Exception, e:
            if f: f.close()
            
            msglog.exception()
           
            raise MpxException('Error reading Configuration MD5: %s' % str(e))
        
    ## 
    # Open the nodedef database 
    # @exception EFileNotFound if nodedef database cannot be located
    #
    def _open_nodedef_db(self):
        try:
            fname = os.path.join(self.BROADWAY_ROOT,self.NODEDEF_DBFILE)
            f = open(fname)
            return f
        except:
            raise EFileNotFound('Node Def database (%s) was not found' % fname)


    ##
    # Replace the contents of the Broadway XML configuration file.
    # This has no effect on the running configuration.
    # @param text The string to use ro replace the contents of the Broadway
    #             XML configuration file.
    # @exception EInvalidXML
    # @todo Make sure that parse_xml returns good exceptions and does decent
    #       validation.
    def write(self, text):
        # Generate a name for the temp file
        tmpname = os.path.join( properties.TEMP_DIR, '__TMP__XML__' ) \
                + str( randrange( 0, 999999999, 1) )

        # Validate the XML by copying it to a temporary file and checking it
        # with parse_xml..
        tmpfile = open(tmpname,'w+')
        invalid_xml = 1
        try:
            tmpfile.write(text)
            tmpfile.flush()
            parse_xml(tmpname)
            invalid_xml = 0
        finally:
            # Try really hard to discard the temporary file.
            try: tmpfile.close()
            except: msglog.exception()
            try: os.unlink(tmpname)
            except: msglog.exception()
            if invalid_xml:
                raise EInvalidXML
        # If we get here, at 'looks' like a valid configuration.
        # OK, here comes the scary bit.
        # Try to save old configuration.
        old_config_name = None
        config_file_full = properties.CONFIGURATION_FILE
        paths = config_file_full.split('/')        
        config_file = paths[-1]
        config_path = config_file_full[0:-len(config_file)]

        
        if os.path.exists(config_path):
            if os.path.exists(config_file_full):
                old_config_name = os.path.join(config_path, 'broadway_old.xml')
                os.rename(config_file_full, old_config_name)
        else:
            # The config path does not exist, try to create it.
            os.makedirs(config_path)
        all_ok = 0
        try:
            newfile = open(config_file_full, 'w+')
            newfile.write(text)
            newfile.close()
            all_ok = 1
        finally:
            # I use a finally block so a meaningful exception is raised.
            if not all_ok and old_config_name:
                os.rename(old_config_name, config_file_full)
    ##
    # Exit the Broadway framework.  If Broadway in running in the context of
    # an MPX embedded (or similiarly configured) system, then it will restart
    # after exiting.
    # @param flag How to exit the framework.
    # @value mpx.service.configuration.SOFT_EXIT Exit Broadway entirely
    #                                            through framework software.
    # @value mpx.service.configuration.HARD_EXIT Reboot the system.  This is
    #                                            an extreme measure!
    # @note There is a 5 second delay after the method returns before the
    #       framework exits.  This is so programs comminicating via RNA, will
    #       get a good response and 'know' that the request has been scheduled.
    def exit(self,flag):
        try: urllib2.urlopen("http://localhost:8080/GlobalNavigation/SychDatabase")
        except  Exception, e: pass
        _exit(flag)

