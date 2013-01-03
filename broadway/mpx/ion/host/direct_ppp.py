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
from mpx.lib import threading
from mpx.lib.node import CompositeNode, ConfigurableNode
from mpx.service.network import ConnectionMixin
from mpx.lib.event import ConnectionEvent, EventProducerMixin
from mpx.lib.exceptions import ETimeout, EConnectionError,\
                               EPermission, EConfigurationInvalid,\
                               EFileNotFound, ENotEnabled
from mpx.lib.configure import REQUIRED, set_attribute, get_attribute
from mpx.lib import msglog
from moab.linux.lib.servicemgr import InittabManager, InittabGroup
from moab.linux.lib.confighelper import *

from mpx.ion.host.modem.ppp import PPP

_autoppp_comment = """
#
# Automatic PPP startup on receipt of LCP configure request (AutoPPP).
#  mgetty has to be compiled with "-DAUTO_PPP" for this to work.
#  Warning: Case is significant, AUTOPPP or autoppp won't work!
#  Consult the "pppd" man page to find pppd options that work for you.
#
#  NOTE: for *some* users, the "-detach" option has been necessary, for 
#        others, not at all. If your pppd doesn't die after hangup, try it.
#
#  NOTE2: "debug" creates lots of debugging info.  LOOK AT IT if things
#         do not work out of the box, most likely it's a ppp problem!
#
#  NOTE3: "man pppd" is your friend!
#
#  NOTE4: max. 9 arguments allowed.
#
"""


# NOTE:  Most of this will probably go away very shortly.

##
# PPP node to enable connecting and disconnecting
# throughout framework.  Node is a singleton because
# an MPX currently can have at most one PPP connection.
# @note  PPP node is threadsafe and keeps a connection
#        count to determine when to connect and to 
#        disconnect PPP connection.
class DirectPPP( CompositeNode ):
    def __init__( self ):      
        CompositeNode.__init__( self )
        Incoming().configure( {'name':'incoming', 'parent':self} )
        
    def configure( self, config ):
        CompositeNode.configure( self, config )
        set_attribute( self, 'debug_flag', 0, config )        
        set_attribute( self, 'enable', 1, config )        
        
    def configuration( self ):
        config = CompositeNode.configuration( self )
        get_attribute( self, 'debug_flag', config )        
        get_attribute( self, 'enable', config )        
        return config


class Incoming( ConfigurableNode, ConnectionMixin, EventProducerMixin ):  
    def __init__( self ):
        ConfigurableNode.__init__( self )
        ConnectionMixin.__init__( self )
        EventProducerMixin.__init__( self )
        self.critical_data = self._CriticalData()
        self.port = None
 
    def _start_ppp_program( self ):
        inittab = InittabManager()
        port_name = self._getPortName()
        tag = port_name[-2:]
        gname = 'MPX_MGETTY_%s' % port_name.upper()
        if self.enable:
            if not inittab.findgroup( gname ):
                inittab.addgroup( 
                    InittabGroup( gname, '%s:2345:respawn:/sbin/mgetty -x 0 -n 1 %s' % (tag, port_name) ) )
        else:
            inittab.remgroup( gname )
        inittab.commit()
        
    def _enable_direct_ppp( self ):
        cf = MgettyConfig()
        cf.addPort( self._getPortName(),
                    "  direct yes\n  speed %d\n  data-only yes\n  toggle-dtr no\n" % self.port.baud )
        cf.save()
        
        login_prog = '/usr/sbin/pppd auth -chap +pap login debug %s:%s'
        cf = LoginConfig()
        cf.addUser( '/AutoPPP/', '-', 'a_ppp',
                    login_prog % (self.local_ip, self.client_ip),
                    _autoppp_comment )
        cf.save()
        
        cf = PAPSecrets()
        cf.addClient( self.user_id, '*', self.password, '*' )
        cf.save()
            
    def _disable_direct_ppp( self ):
        cf = LoginConfig()
        cf.removeUser( '/AutoPPP/' )
        cf.save()
            
    def configure( self, config ):
        set_attribute( self, 'enable', 0, config, int )   
        set_attribute( self, 'user_id', '', config )   
        set_attribute( self, 'password', '', config )   
        set_attribute( self, 'local_ip', '', config )   
        set_attribute( self, 'client_ip', '', config )   
        set_attribute( self, 'debug', 0, config, int )         
        ConfigurableNode.configure( self, config )
        
            
    def configuration(self):
        config = ConfigurableNode.configuration( self )
        get_attribute( self, 'enable', config )        
        get_attribute( self, 'user_id', config )        
        get_attribute( self, 'password', config )        
        get_attribute( self, 'local_ip', config )        
        get_attribute( self, 'client_ip', config )        
        get_attribute( self, 'debug', config )        
        return config
    
    def start( self ):
        #
        # Should I also call ConnectionMixin.start() and 
        # EventProducerMixin.start()????
        ConfigurableNode.start( self )
        msg = ''
        _msg = ''
        
        # This node is a child of DirectPPP, which in turn is a child of a Port.
        self.port = self.parent.parent
        
        try:
            if self.enable:
                _msg =  ( '%s.%s did not start..\nReason\n'
                          % (str( self.parent.name ), str( self.name )) )
                self._enable_direct_ppp()
                self._start_ppp_program()
            else:
                _msg = ( 'Could not disable %s.%s ' 
                         % (self.parent.name, self.name) )
                self._disable_direct_ppp()    
                self._start_ppp_program()
                
        except EPermission, e:
            msg += _msg
            msg += str( e.keywords['reason'] )
        except EFileNotFound, e:
            msg += _msg
            msg += 'File: '  + str(e)
        except IOError, e:
            msg += _msg
            msg += 'File Error!\n'
            msg +=  e.strerror + '\n'
            msg += 'File: ' + str( e.filename )
        except Exception, e:
            msglog.exception()
            msg += _msg
            msg += 'Exception: ' + str( e )
        if msg:            
            self.enable = 0
            msglog.log( 'broadway', msglog.types.ERR, msg )  
        else:
            if self.enable:
                msg = (str( self.parent.name ) + '.' 
                       + str( self.name ) + ' started..')
                msglog.log( 'broadway', msglog.types.INFO, msg )  
            else:
                msg = ('%s.%s service is NOT enabled.' 
                       % (self.parent.name, self.name))
                msglog.log( 'broadway', msglog.types.INFO, msg )

    def acquire( self, timeout = None ):
        if not self.enable:
            raise ENotEnabled( '%s service is NOT enabled' % self.name ) 
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
                # need to figureout timeout
                self.critical_data.wait( timeout )
                if self.critical_data.get_state() == ConnectionMixin.UP:
                    rt = self.critical_data.increment_connection_count()
                else:
                    rt = 0  
        finally:
            if got_lock:
                self.critical_data.release()
        return rt 
    
    def release( self ):
        self.critical_data.acquire()
        try:
            if self.critical_data.connection_count < 0:
                self.critical_data.connection_count = 0
        finally:
            self.critical_data.release()


#_dppp_singleton = None
    
#def factory():
#    global _dppp_singleton
#    if _dppp_singleton == None:
#        _dppp_singleton = DirectPPP()
#    return _dppp_singleton

def factory():
    return PPP()
