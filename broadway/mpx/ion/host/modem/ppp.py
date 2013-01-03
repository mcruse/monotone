"""
Copyright (C) 2002 2003 2004 2006 2010 2011 Cisco Systems

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
# @todo  This object will no longer be a singleton
#        and will have ppp connection configuration
#        information associated with it once we move
#        the ppp functionality and configuration out
#        of mpxconfig.
# @note  The reason this is currently a singleton is because
#        there is only one ppp connection currently available on 
#        mpx's and we need to keep an accurate connection count 
#        even if multiple instances (not really because singleton) 
#        are created and used in the system.

import time
import traceback
import os
import ConfigParser
from mpx import properties
from mpx.lib import msglog, threading, _ppp
from mpx.lib.node import CompositeNode, as_node_url
from mpx.lib.event import ConnectionEvent, EventProducerMixin
from mpx.lib._ppp import  EPppErrantProcess,\
     EPppConnectionTimedOut, EPppDeviceLocked
from mpx.ion.host.modem import Modem, InternalModem
from mpx.ion.host.port import int_to_flowctl
from mpx.lib.exceptions import ETimeout, EConnectionError,\
     EPermission, EConfigurationInvalid, EFileNotFound, ENotEnabled,\
     EInvalidValue
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute, \
     as_boolean, as_onoff
from moab.linux.lib.servicemgr import InittabManager, InittabGroup
from moab.linux.lib.confighelper import PAPSecrets, CHAPSecrets, MgettyConfig, LoginConfig
from mpx.service.network import ConnectionMixin

debug = 0

stdcomment = """
# This is the "standard" behaviour - *dont* set a userid or utmp
#  entry here, otherwise /bin/login will fail!
#  This entry isn't really necessary: if it's missing, the built-in
#  default will do exactly this.
#
"""

##
# A class which adds the ability to save configuration information
# to the mpxconfig configuration file as needed to those nodes
# which need to do so.
class SaveConfigMixin:
    def __init__( self, config_section ):
        self._CONFIG_SECTION = config_section
    #
    def _get_config_parser( self ):
        cf = properties.MPXINIT_CONF_FILE
        if os.access( cf, os.F_OK|os.R_OK|os.W_OK ):
            f = open( cf, 'r' )
            cp = ConfigParser.ConfigParser()
            cp.readfp( f )
            f.close()
        else:
            if not os.access( cf, os.F_OK ):
                raise EFileNotFound( "%s not found" % cf )
            elif not os.access( cf, os.R_OK ):
                raise EPermission( reason = 'Cannot read file %s' %  cf )
            elif not os.access( cf, os.W_OK ):
                raise EPermission( reason = 'Cannot write file %s' % cf )
        return cp
    #
    ##
    # Save parameters as a convenience for mpxconfig utility.
    #
    def _save_config( self, config_dict ):
        if debug:
            print 'In _save_config with %s and %s.' % (self._CONFIG_SECTION,
                                                       str(config_dict))
        cp = self._get_config_parser()
        
        if not cp.has_section( self._CONFIG_SECTION ):
            cp.add_section( self._CONFIG_SECTION )
        if self.enable == 1:
            cp.set( self._CONFIG_SECTION, 'state', 'enabled' )
        elif self.enable ==0:
            cp.set( self._CONFIG_SECTION, 'state', 'disabled' )
        else:
            raise EConfigurationInvalid(
                'Config value for "state" is invalid...\n'
                'requested state: %s\n'
                'valid states: enabled(1) or disabled(0)' % str( self.enable ) )
        
        for option in config_dict.keys():
            cp.set( self._CONFIG_SECTION, option, config_dict[option] )
        
        f = open( properties.MPXINIT_CONF_FILE, 'w' )
        cp.write( f )
        f.close()


##
# PPP node to enable connecting and disconnecting throughout framework.
# @note  PPP node is threadsafe and keeps a connection count to determine
#        when to connect and to disconnect PPP connection.
#
class PPP( CompositeNode ):
    def __init__( self ):      
        CompositeNode.__init__( self )
        Incoming().configure( {'name':'incoming', 'parent':self} )
        Outgoing().configure( {'name':'outgoing', 'parent':self} )
        
    def configure( self, config ):
        # Handle debug_flag which can be set by the Direct PPP node,
        # but let debug override it if it is specified.
        if config.has_key('debug_flag'):
            if not config.has_key('debug'):
                config['debug'] = config['debug_flag']
        set_attribute( self, 'debug', 0, config )
        set_attribute( self, 'override_defaultroute', 1, config, int )
        set_attribute( self, 'noipdefault', 1, config, int )
        set_attribute( self, 'mtu', 876, config, int)
        set_attribute( self, 'mru', 876, config, int)
        set_attribute( self, 'advanced_options', [], config)
        CompositeNode.configure( self, config )
        
    def configuration( self ):
        config = CompositeNode.configuration( self )
        get_attribute( self, 'debug', config )
        get_attribute( self, 'override_defaultroute', config )
        get_attribute( self, 'noipdefault', config )
        get_attribute( self, 'mtu', config )
        get_attribute( self, 'mru', config )
        get_attribute( self, 'advanced_options', config )
        return config


##
# Class to encapsulate the common features of children of the PPP node.
#
class PPPChildNode( CompositeNode, ConnectionMixin, EventProducerMixin ):
    def __init__( self, log_id ):
        CompositeNode.__init__( self )
        ConnectionMixin.__init__( self )
        EventProducerMixin.__init__( self )
        self.critical_data = self._CriticalData()
        self._log_id = log_id
        self._service_name = None
        self._device = None
        self._port = None
      
    def configure( self, config ):
        set_attribute( self, 'enable', 0, config, int )   
        set_attribute( self, 'debug', 0, config, int )
        CompositeNode.configure( self, config)
        
    def configuration( self ):
        config = CompositeNode.configuration( self )
        get_attribute( self, 'enable', config ) 
        get_attribute( self, 'debug', config ) 
        return config

    def _is_parent_modem( self ):
        self._get_device_node()
        return isinstance( self._device, Modem )

    def _is_parent_internal_modem( self ):
        self._get_device_node()
        if not self._is_parent_modem():
            return 0
        return isinstance( self._device, InternalModem )

    def _get_device_node( self ):
        # Note: At this time, the device associated with a PPP Child Node
        #       is always the parent of its parent.
        self._device = self.parent.parent
        return self._device
        
    def _get_port_node( self ):
        if self._port:
            return self._port
        self._get_device_node()
        #
        if self._is_parent_modem() and (not self._is_parent_internal_modem()):
            self._port = self._device.port
        else:
            # For both serial ports and internal modems, the port node
            # is the same as the device node
            self._port = self._device
        #
        return self._port

    def _get_port_name( self ):
        pnode = self._get_port_node()
        return os.path.split( pnode.dev )[1]

    def _get_flow_control_str( self ):
        pnode = self._get_port_node()
        fstr = int_to_flowctl(pnode.flow_control)
        return fstr
    
    def _get_translated_flow_control_name( self ):
        fc = self._get_flow_control_str()
        if fc == 'none':
            fc = 'nocrtscts'
        elif fc == 'xon/xoff':
            fc = 'xonxoff'
        elif fc == 'hardware' or fc == 'rts/cts':
            fc = 'crtscts'
        else:
            estr = "Couldn't map flow control of %s for %s and %s." % (str(fc),
                                                                       str(self),
                                                                       str(self._port))
            raise EInvalidValue('flow_control', fc, estr)
        return fc

    ##
    # Wrapper around the *real* start method to do common pre- and post- processing.
    #
    def start( self ):
        #
        # Should I also call ConnectionMixin.start() and 
        # EventProducerMixin.start()????
        CompositeNode.start( self )
        msg = ''
        msg_prefix = ''

        # Invoke the *real* start method.
        try:
            if self.enable:
                msg_prefix = "%s did not start:\n" % self._get_service_name()
            else:
                msg_prefix = "Could not disable %s:\n" % self._get_service_name()
            self._start()                   

        except EConfigurationInvalid, e:
            msg = msg_prefix + str( e )
        except EPermission, e:
            msg = msg_prefix + str( e.keywords['reason'] )
        except EFileNotFound, e:
            msg = msg_prefix + 'File: ' + str( e )
        except IOError, e:
            msg = msg_prefix
            msg += 'File Error!\n'
            msg +=  e.strerror + '\n'
            msg += 'File: ' + str( e.filename )
        except Exception, e:
            msglog.exception()
            msg = msg_prefix
            msg += str( e )
            
        if msg:            
            self.enable = 0
            msglog.log( 'broadway', msglog.types.ERR, msg )  
        elif self.enable:
            msg = "%s started..." % self._get_service_name()
            msglog.log( 'broadway', msglog.types.INFO, msg )  
        else:
            msg = "%s service is NOT enabled." % self._get_service_name()
            msglog.log( 'broadway', msglog.types.INFO, msg )

    def _start( self ):
        # Subclass must provide this method.
        raise NotImplementedError
    
    def _get_service_name( self ):
        if not self._service_name:
            self._service_name = "%s.%s.%s" % (self.parent.parent.name, self.parent.name, self.name)
            # Add comm node name if external modem.
            if not self._is_parent_internal_modem():
                self._service_name = "%s.%s" % (self.parent.parent.parent.name, self._service_name)
        return self._service_name

    def _raise_econfiguration_invalid( self, filename, reason ):
        msg = 'Invalid Configuration for file: %s\n%s\n' \
              'Check file %s\nsection="%s" for config information' \
            % ( filename, reason, str(properties.MPXINIT_CONF_FILE), self._CONFIG_SECTION )
        raise EConfigurationInvalid( msg )

    def _generate_file( self, filename, lines ):
        f = open( filename, 'w+' )
        f.writelines( lines )
        f.close()
        os.chmod( filename, (os.R_OK|os.W_OK) << 6 )

    def _msglog( self, msg ):
        if self.__dict__.has_key( 'debug' ):       
            if self.debug:
                msglog.log( self._log_id, msglog.types.DB, msg )

    def _gen_ppp_options( self, comment ):
         ppp_options_dict = {'comment':comment, 'userid':self.user_id,
                             'noipdefault':self.parent.noipdefault,
                             'mtu':self.parent.mtu, 'mru':self.parent.mru,
                             'chat_filename':None,
                             'usepeerdns':None, 'passive':None,
                             'usehostname':None,
                             'advanced_options':self.parent.advanced_options,
                             'local_ip':None, 'client_ip':None,
                            }
         return ppp_options_dict
     
    def _format_ppp_options( self, podict ):
        pnode = self._get_port_node()
        
        options = [podict['comment'],
                   '%s\n' % pnode.dev,
                   '%s\n' % pnode.baud,
                   '%s\n' % self._get_translated_flow_control_name(),
                   'asyncmap 0\n',
                   ]
        if podict['passive']:
            options.append('passive\n')
        if podict['usehostname']:
            options.append('usehostname\n')
        if podict['usepeerdns']:
            options.append('usepeerdns\n')
        if self._is_parent_modem():
            options.append('modem\n')
        else:
            options.append('local\n')
        if podict['chat_filename']:
            options.append( 'connect "chat -v -f %s"\n' % podict['chat_filename'] )
        if len( podict['userid'] ) > 0:
            options.append( 'user %s\n' % podict['userid'] )
        if podict['noipdefault']==1:
            options.append( 'noipdefault\n' )
        options.append( 'mtu %d\n' % podict['mtu'] )
        options.append( 'mru %d\n' % podict['mru'] )
        if podict['local_ip'] and podict['client_ip']:
            options.append('%s:%s\n' % (podict['local_ip'],
                                        podict['client_ip']))
        for x in podict['advanced_options']:
            if x['parmname']:
                options.append( x['parmname'] )
                if x['parmvalue']:
                    options.append( ' %s\n' % x['parmvalue'] )
                else:
                    options.append( '\n' )
        
        return options


class Outgoing( PPPChildNode, SaveConfigMixin ):
    def __init__( self ):
        PPPChildNode.__init__( self,
                               'broadway.mpx.ion.host.modem.ppp.outgoing')
        SaveConfigMixin.__init__( self, 'dialout' )
        self.critical_data.set_state( ConnectionMixin.DOWN )
        self.ppp = _ppp.PPP()
        return
    def _gen_chat_script( self, comment ):
        dnode = self._get_device_node()
        chat_script = dnode.getChatScript( comment, self.phone_number )
        self._generate_file( self.chat_file_name, chat_script )

    def _gen_ppp_options( self, comment ):
        ppp_options_dict = PPPChildNode._gen_ppp_options( self, comment )

        ppp_options_dict['chat_filename'] = self.chat_file_name
        ppp_options_dict['usepeerdns'] = 1

        dnode = self._get_device_node()
        if hasattr(dnode, 'override_outgoing_ppp_options'):
            self._device.override_outgoing_ppp_options(ppp_options_dict)
        
        options = self._format_ppp_options(ppp_options_dict)
        
        self._generate_file( self.ppp_file_name, options )

    ##
    # Save user id and password in PAP secrets file.
    #
    def _gen_pap_secrets( self ):
        # Nothing to do if there's no user id.  Not all PPP connections require one.
        # For example, wireless modems.
        if len( self.user_id ) > 0:
            if not len( self.password ) > 0:
                self._raise_econfiguration_invalid( properties.PAP_SECRETS_FILE,
                                                    'No password')       
            secrets = PAPSecrets( properties.PAP_SECRETS_FILE )
            secrets.addClient( self.user_id, "*", self.password, "*" )
            secrets.save()
    
    def _gen_chap_secrets( self ): 
        # Nothing to do if there's no user id.  Not all PPP connections require one.
        # For example, wireless modems.
        if len( self.user_id ) > 0:
            if not len( self.password ) > 0:
                self._raise_econfiguration_invalid( properties.CHAP_SECRETS_FILE,
                                                    'No password')       
            secrets = CHAPSecrets( properties.CHAP_SECRETS_FILE )
            secrets.addClient( self.user_id, "*", self.password, "*" )
            secrets.save()

    def _update_nameservers_file( self, clean = 0 ): 
        marker = '# next line added by the broadway framework for port %s\n' % self._get_port_name()
        
        f = open( properties.NAMESERVERS_FILE, 'r+' )
        f.seek( 0 )
        lines = f.readlines()

        # Remove any previously added lines
        i_line = 0
        line_count = len(lines)
        while i_line < line_count:
            if lines[i_line] == marker:
                del lines[i_line]
                del lines[i_line]
                line_count -= 2
            else:
                i_line += 1
                
        if not clean:
            nameservers = []
            if len( self.primary_name_server ) > 0:
                nameservers.append( self.primary_name_server )
            if len( self.secondary_name_server ) > 0:
                nameservers.append( self.secondary_name_server )
                         
            # Add new lines
            for dns in nameservers:
                lines.append( marker )
                lines.append( 'nameserver %s\n' % dns )
            f.seek( 0 )
            if lines:
                f.writelines( lines )
            else:
                f.write( '' )
            
        f.close()     
        
    def _setup_options_file( self ):
        comment = '# Script generated by the broadway framework\n' \
                  '# Date: %s for %s\n' % ( str( time.ctime( time.time() ) ),
                                               as_node_url( self ) )
        
        cf = properties.MPXINIT_CONF_FILE
        
        # Create CHAT file specific to this port.    
        self._gen_chat_script( comment )
        
        # Create ppp options specific to this port.
        self._gen_ppp_options( comment )
         
        # Create chap secrets.
        self._gen_chap_secrets()
        
        # Create pap secrets.
        self._gen_pap_secrets()
        
        # Update nameservers.
        self._update_nameservers_file()

    ##
    # Save parameters as a convenience for mpxconfig utility.
    #
    def _update_config_file( self ):
        # Currenly only save config info for internal modem and if
        # we have the SaveConfigMixin mixed-in.
        if self._is_parent_internal_modem() and hasattr(self, '_save_config'):
            config_dict = {'connect_speed' : self._get_device_node().port.baud,
                           'flow_control'  : self._get_flow_control_str(),
                           'phone'         : self.phone_number,
                           'userid'        : self.user_id,
                           'password'      : self.password,
                           'dns1'          : self.primary_name_server,
                           'dns2'          : self.secondary_name_server}
            self._save_config( config_dict )
            
    def _get_service_tag_name( self ):
        return "P%s" % self._get_port_name()[-2:]
        
    def _disable( self ):
        self.ppp.stop_service( self._get_service_tag_name() )
        if os.path.isfile( self.chat_file_name ):
            os.remove( self.chat_file_name )
        if os.path.isfile( self.ppp_file_name ):
            os.remove( self.ppp_file_name )
        self._update_nameservers_file( clean = 1 )

    def _connect( self, timeout = None ):
        self._msglog("connect timeout is %s, opt file is %s" %
                     (str(timeout), self.ppp_file_name))
        if not self.ppp.is_connected():
            self.ppp.connect( timeout, self.ppp_file_name, self.routes )
        return
    def _disconnect( self ):
        if self.ppp.is_connected():
            self.ppp.disconnect()
        return
    def configure( self, config ):
        PPPChildNode.configure( self, config )
        set_attribute( self, 'on_demand', 1, config, int )   
        set_attribute( self, 'phone_number', '', config, str )   
        set_attribute( self, 'user_id', '', config, str )   
        set_attribute( self, 'password', '', config, str )   
        set_attribute( self, 'primary_name_server', '', config, str )   
        set_attribute( self, 'secondary_name_server', '', config, str )
        set_attribute( self, 'routes', [], config)
        return
    def configuration( self ):
        config = PPPChildNode.configuration( self )
        get_attribute( self, 'on_demand', config ) 
        get_attribute( self, 'phone_number', config )    
        get_attribute( self, 'user_id', config )  
        get_attribute( self, 'password', config )    
        get_attribute( self, 'primary_name_server', config )  
        get_attribute( self, 'secondary_name_server', config )
        get_attribute( self, 'routes', config )
        return config    
    def _start( self ):
        self.chat_file_name = "%s.%s" % (properties.CHAT_SCRIPT_FILE,
                                         self._get_port_name())
        self.ppp_file_name = "%s.%s" % (properties.PPP_DIALOUT_OPTIONS_FILE,
                                        self._get_port_name())

        if self.parent.override_defaultroute:
            self._msglog("Clearing don't override default route flag.")
            self.ppp.set_override_default_route( 1 )
        else:
            self._msglog("Setting don't override default route flag.")
            self.ppp.set_override_default_route( 0 )
            
        if self.enable:
            self._update_config_file()
            self._setup_options_file()
            if not self.on_demand:
                self.ppp.start_service( self._get_service_tag_name(),
                                        self.ppp_file_name )
            else:
                self.ppp.stop_service( self._get_service_tag_name() )
        else:
            self._disable()
            
    def get_status( self ):
        self.critical_data.acquire()
        ret = self.critical_data.get_state()
        self.critical_data.release()
        return ret

    def acquire( self, timeout = 60 ):
        if not self.enable:
            raise ENotEnabled( '%s service is NOT enabled' %
                               self._get_service_name() )
        if not self.on_demand:
            # Assume pppd is running.  Any way to verify?
            return 1
        end_time = time.time() + timeout
        got_lock = 0
        self.critical_data.acquire()
        got_lock = 1
        rt = None
        timeout_msg = 'PPP connection timed out.. '
        timeout_msg += 'Current TIMEOUT: ' + str(timeout)
        try:
            # First, check to see if we think we have a connection, but it
            # was lost somehow.
            if self.critical_data.get_state() == ConnectionMixin.UP:
                if not self.ppp.is_connected():
                    # Yes it was lost, go ahead and set our state to
                    # reflect that fact.
                    self.critical_data.set_state(ConnectionMixin.DOWN)
            try:
                if self.critical_data.get_state() == ConnectionMixin.DOWN:
                    self.critical_data.set_state(ConnectionMixin.CONNECTING)
                    self.critical_data.release()
                    got_lock = 0
                    self._msglog('Trying to connect..')
                    self._connect(timeout)
                    self.critical_data.acquire()
                    got_lock = 1
                    self.critical_data.set_state(ConnectionMixin.UP)
                    self.critical_data.notify()
                    self._msglog('Connected...')
                    rt = self.critical_data.increment_connection_count()
                elif self.critical_data.get_state() == ConnectionMixin.CONNECTING or \
                     self.critical_data.get_state() == ConnectionMixin.DISCONNECTING:
                    self._msglog('Current Status is ' + str(self.critical_data.get_state()))
                    timeout = end_time - time.time()
                    if timeout > 0:  
                        self._msglog('Waiting')
                        self.critical_data.wait(timeout)
                        timeout = end_time - time.time()
                        self._msglog( 'State ' + str(self.critical_data.get_state()))
                        if self.critical_data.get_state() == ConnectionMixin.DOWN:
                            timeout = end_time - time.time()
                            if timeout > 0:                                
                                self.critical_data.set_state(
                                    ConnectionMixin.CONNECTING
                                    )
                                self.critical_data.release()
                                got_lock = 0
                                self._connect(timeout)
                                self.critical_data.acquire()
                                got_lock = 1
                                self.critical_data.set_state(
                                    ConnectionMixin.UP
                                    )
                                rt = self.critical_data.increment_connection_count()
                                self.critical_data.notify()
                            else:
                                self.critical_data.set_state(
                                    ConnectionMixin.DOWN
                                    )
                                self.critical_data.notify()
                                raise ETimeout('Thread waiting for access to outgoing PPP connection was awakened too late.')
                        else:
                            self._msglog('Connection is up!..incrementing count' )
                         
                            rt = self.critical_data.increment_connection_count()
                            self._msglog('RT: ' + str(rt))
                    else:
                        self.critical_data.acquire()
                        got_lock = 1
                        self.critical_data.set_state(ConnectionMixin.DOWN)
                        self.critical_data.notify()
                        raise ETimeout(timeout_msg)
                elif self.critical_data.get_state() == ConnectionMixin.UP:
                    self._msglog('already connected..')
                    rt = self.critical_data.increment_connection_count()
     
            except EPppDeviceLocked,e:
                self.critical_data.acquire()
                got_lock = 1
                self.critical_data.set_state(ConnectionMixin.DOWN)
                self.critical_data.notify()
                raise EConnectionError('PPP: ppp device is locked')
                
            except EPppConnectionTimedOut,e:
                self.critical_data.acquire()
                got_lock = 1
                self.critical_data.set_state(ConnectionMixin.DOWN)
                self.critical_data.notify()
                raise ETimeout(timeout_msg)
            
            except EPppErrantProcess,e:
                self.critical_data.acquire()
                got_lock = 1
                self.critical_data.set_state(ConnectionMixin.DOWN)
                self.critical_data.notify()
                raise EConnectionError('pppd command went crazy!')
            
            except EConnectionError,e:
                self.critical_data.acquire()
                got_lock = 1
                self.critical_data.set_state(ConnectionMixin.DOWN)
                self.critical_data.notify()
                raise
                
        finally:
            if got_lock:
                self.critical_data.release()
        return rt
    
    def release(self):
        if not self.on_demand:
            # Don't disconnect if not on-demand.
            return
        got_lock = 0
        self.critical_data.acquire()
        got_lock = 1
        try:
            self.critical_data.decrement_connection_count()
            if self.critical_data.connection_count == 0:
                self.critical_data.set_state(ConnectionMixin.DISCONNECTING)
                self.critical_data.release()
                got_lock = 0
                self._msglog('disconnecting..')
                self._disconnect()
                self.critical_data.acquire()
                got_lock = 1
                self.critical_data.set_state(ConnectionMixin.DOWN)
                self._msglog('disconnected..')
                pppd_tdb_file_path = '/var/run/pppd.tdb'
                os.system('rm %s' % pppd_tdb_file_path)
                self._msglog('Removed %s.' % pppd_tdb_file_path)
            if self.critical_data.connection_count < 0:
                self.critical_data.connection_count = 0
        finally:
            if got_lock:
                self.critical_data.release()
            
                
class Incoming( PPPChildNode, SaveConfigMixin ):  
    def __init__( self ):
        PPPChildNode.__init__( self, 'broadway.mpx.ion.host.modem.ppp.incoming' )
        SaveConfigMixin.__init__( self, 'dialin' )
    #
    ##
    # Save parameters as a convenience for mpxconfig utility.
    #
    def _update_config_file( self ):
        # Currenly only save config info for internal modem and if
        # we have the SaveConfigMixin mixed-in.
        if self._is_parent_internal_modem() and hasattr(self, '_save_config'):
            config_dict = {'password'     : self.password,
                           'userid'       : self.user_id,
                           'flow_control' : self._get_flow_control_str(),
                           'client_addr'  : self.client_ip,
                           'local_addr'   : self.local_ip}
            self._save_config( config_dict )

    def _gen_ppp_options( self, comment ):
        fc = self._get_translated_flow_control_name()
        if not fc:
            self._raise_econfiguration_invalid(
                self.ppp_file_name, 'Invalid flow control option: %s' % fc )        

        if not len( self.local_ip ) > 0:
            self._raise_econfiguration_invalid( self.ppp_file_name, 'No local IP address' )
             
        if not len( self.client_ip ) > 0:
            self._raise_econfiguration_invalid( self.ppp_file_name, 'No client IP address' )
        
        ppp_options_dict = PPPChildNode._gen_ppp_options( self, comment )

        ppp_options_dict['passive'] = 1
        ppp_options_dict['usehostname'] = 1
        ppp_options_dict['local_ip'] = self.local_ip
        ppp_options_dict['client_ip'] = self.client_ip

        # Make sure no userid is set for dial in
        ppp_options_dict['userid'] = ''

        dnode = self._get_device_node
        if hasattr(dnode, 'override_incoming_ppp_options'):
            self._device.override__incoming_ppp_options(ppp_options_dict)

        options = self._format_ppp_options(ppp_options_dict)
        
        self._generate_file( self.ppp_file_name, options )
   
        #options = [comment, 
        #           'modem\n',
        #           '%s\n' % fc,
        #           'asyncmap 0\n',
        #           'mru %d\n' % self.parent.mru,
        #           'mtu %d\n' % self.parent.mtu,
        #           'passive\n',
        #           'usehostname\n',
        #           '%s:%s\n' % (self.local_ip, self.client_ip)]
    
    def _setup_options_file( self ):
        # Create ppp options
        pnode = self._get_port_node()
        
        comment = '# Script generated by the broadway framework\n' \
                  '# Date: %s for %s\n' % ( str( time.ctime( time.time() ) ),
                                            as_node_url( self ) )
        self._gen_ppp_options( comment )
        
        # mgetty configuration
        mc = MgettyConfig()
        pname = self._get_port_name()
        mstr  = '  speed %d\n' % pnode.baud
        if self._is_parent_modem():
            dnode = self._get_device_node()
            mstr += '  init-chat "" \d%s OK\n' % dnode.init_string
        else:
            mstr += '  direct yes\n'
            mstr += '  data-only yes\n'
            mstr += '  toggle-dtr no\n'
        mstr += '  login-conf-file %s\n' % self.login_config_filename
        
        mc.addPort( pname, mstr)
        mc.save()
               
        # Create chap secrets.
        self._gen_chap_secrets()
        
        # Create pap secrets.
        self._gen_pap_secrets()
        
    ##
    # Save user id and password in PAP secrets file.
    #
    def _gen_pap_secrets( self ):
        # Nothing to do if there's no user id.  Not all PPP connections require one.
        # For example, wireless modems.
        if len( self.user_id ) > 0:
            if not len( self.password ) > 0:
                self._raise_econfiguration_invalid( properties.PAP_SECRETS_FILE,
                                                    'No password')       
            secrets = PAPSecrets( properties.PAP_SECRETS_FILE )
            secrets.addClient( self.user_id, "*", self.password, "*" )
            secrets.save()
    ##
    # Save user id and password in CHAP secrets file.
    #
    def _gen_chap_secrets( self ): 
        # Nothing to do if there's no user id.  Not all PPP connections require one.
        # For example, wireless modems.
        if len( self.user_id ) > 0:
            if not len( self.password ) > 0:
                self._raise_econfiguration_invalid( properties.CHAP_SECRETS_FILE,
                                                    'No password')       
            secrets = CHAPSecrets( properties.CHAP_SECRETS_FILE )
            secrets.addClient( self.user_id, "*", self.password, "*" )
            secrets.save()
            
    def _update_user_password( self ):
        if not len( self.user_id ) > 0:
            self._raise_econfiguration_invalid( self.ppp_file_name, 'No user id' )
        
        if not len( self.password ) > 0:
            self._raise_econfiguration_invalid( self.ppp_file_name, 'No password' )

        command = "echo %s | passwd --stdin %s 1>/dev/null 2>&1" % (self.password, self.user_id)
        err = os.system( command )
        if err != 0:
            raise Exception( "Had a problem updating the PPP user's password\n"
                             "Check userid and password for %s.%s\n" % (self.parent.name, self.name))

    def _enable_auto_ppp( self, enable ):
        #login_prog = '/usr/sbin/pppd auth -chap +pap login debug %s:%s' % (self.local_ip, self.client_ip)
        login_prog = '/usr/sbin/pppd auth +pap debug file %s' % self.ppp_file_name
        
        cf = LoginConfig(self.login_config_filename)
        username = '/AutoPPP/'
        if enable:
            cf.addUser( username, '-', 'a_ppp',
                        login_prog, '# Set up Auto PPP\n' )
        else:
            cf.removeUser( username )
       
        cf.addUser( "*", '-', '-', '/bin/login @', stdcomment)
        cf.save()
        
    def _start_mgetty( self ):
        inittab = InittabManager()
        port = self._get_port_name()
        gname = 'MPX_MGETTY_%s' % port.upper()

        if self.enable:
            loglevel = 0
            if self.debug:
                loglevel = 9
            else:
                # Remove stale mgetty log if not debugging.  No sense using
                # TARGET_ROOT here since mgetty doesn't know anything about it.
                logfile = "/var/log/mgetty.log.%s" % port
                if os.path.isfile( logfile ):
                    os.remove( logfile )

            tag = port[-2:]
            if not inittab.findgroup( gname ):
                inittab.addgroup(
                    InittabGroup(gname,
                                 '%s:2345:respawn:/sbin/mgetty -x %d -n 1 %s'
                                 % (tag, loglevel, port))
                    )
        else:
            inittab.remgroup( gname )

        inittab.commit()
            
    def _disable( self ):
        if os.path.isfile( self.ppp_file_name ):
            os.remove( self.ppp_file_name )
        
        # Remove port from mgetty configuration.
        mc = MgettyConfig()
        mc.removePort( self._get_port_name() )
        mc.save()

    def configure( self, config ):
        PPPChildNode.configure( self, config )
        set_attribute( self, 'user_id', '', config )
        set_attribute( self, 'password', '', config )
        set_attribute( self, 'local_ip', '', config )
        set_attribute( self, 'client_ip', '', config )
        set_attribute( self, 'enable_autoppp', 0, config, int )
            
    def configuration( self ):
        config = PPPChildNode.configuration( self )
        get_attribute( self, 'user_id', config )
        get_attribute( self, 'password', config )
        get_attribute( self, 'local_ip', config )
        get_attribute( self, 'client_ip', config )
        get_attribute( self, 'enable_autoppp', config, as_boolean )
        
        return config
    
    def _start( self ):
        self.ppp_file_name = "%s.%s" % (properties.PPP_DIALIN_OPTIONS_BASE,
                                        self._get_port_name())
        self.login_config_filename = "%s.%s" % (properties.LOGIN_CONFIG_BASE,
                                                self._get_port_name())
        if self.enable:
            self._update_config_file()
            self._setup_options_file()
            self._start_mgetty()
            # Only update the password if we aren't using Auto PPP
            if not self.enable_autoppp:
                self._update_user_password()
            else:
                self._enable_auto_ppp(1)
        else:
            self._update_config_file()
            self._start_mgetty()
            self._disable()
            self._enable_auto_ppp(0)

    def acquire( self, timeout = 60 ):
        if not self.enable:
            raise ENotEnabled( '%s service is NOT enabled' % self._get_service_name() ) 

        rt = 0
        got_lock = 0
        self.critical_data.acquire()
        got_lock = 1
        try:
            if self.critical_data.get_state() == ConnectionMixin.UP:
                rt = self.critical_data.increment_connection_count()
            elif self.critical_data.get_state() == ConnectionMixin.DOWN:
                rt = 0
            elif (self.critical_data.get_state() == ConnectionMixin.CONNECTING
                  or (self.critical_data.get_state() ==
                      ConnectionMixin.DISCONNECTING)):
                # need to figure out timeout
                self.critical_data.wait( timeout )
                if self.critical_data.get_state() == ConnectionMixin.UP:
                    rt = self.critical_data.increment_connection_count()
                else:
                    rt = 0  
        finally:
            if got_lock:
                self.critical_data.release()
        return rt 
    
    def release(self):
        self.critical_data.acquire()
        try:
            if self.critical_data.connection_count < 0:
                self.critical_data.connection_count = 0
        finally:
            self.critical_data.release()
        
 
def factory():
    return PPP()
