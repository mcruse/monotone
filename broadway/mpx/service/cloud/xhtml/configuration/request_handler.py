"""
Copyright (C) 2010 2011 Cisco Systems

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
# Refactor 2/11/2007
import string
import time
import urllib
import urllib2
import cPickle
import os
import socket
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.lib.node import as_internal_node
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.service.cloud.manager import FormationUpdated
from mpx.lib import msglog
from mpx.lib.node import as_node
from mpx.lib.node import as_node_url
from mpx.lib.configure import as_boolean

def valid_hostname(hostname):
    """Checks for the validity of hostname.

    It checks following criteria to make sure whether hostname is valid or not
    	1. Hostname should not be more than 255 characters long.
	2. Periods(.) can used to divide hostname into labels.
	3. Each label should not be more than 63 characters long.
        4. Length of any label should not be zero (or in other words, two consecutive periods are not allowed).
        5. Only alphabets, digits and hyphens are allowed to be part of a label, but label must not start or end with hyphen.
        6. Last label must start with an alphabet.
    """
    
    if len(hostname) == 0 or len(hostname) > 255:
        return False
    hostname_parts = string.split(hostname, '.')
    for i in hostname_parts:
        if len(i) == 0:		#two consecutive periods not allowed
            return False
        if len(i) > 63:		#maximum length 63
            return False
        if (i[0] not in string.ascii_letters) and (i[0] not in string.digits):
            return False
        if (i[len(i) - 1] not in string.ascii_letters) and (i[len(i) - 1] not in string.digits):
            return False
        for j in i:
            if (j not in string.ascii_letters) and (j not in string.digits) and (j != '-'):
                return False
    if hostname_parts[len(hostname_parts) - 1][0] not in string.ascii_letters: #first letter of tld should be alphabet
        return False
    return True

def valid_ip_address(ip_address):
    ip_address_parts = string.split(ip_address, '.')
    if len(ip_address_parts) != 4:
        return False
    for x in ip_address_parts:
        try:
            x = int(x)
        except ValueError:
            return False
        else:
            if x < 0 or x > 255:
                return False
    return True

def get_ip_addr(host):
    if(valid_ip_address(host)):
        return(host)
    
    try:
        ip=socket.gethostbyname(host)
    except socket.error ,msg :
        msglog.log('CloudManager', msglog.types.WARN, 'Unable to resolve the hostname=%s Error message=%s' %(host,msg))
        return(host)    
    return(ip)
    


class CloudConfigurator(CompositeNode):
    def __init__(self, *args, **kw):
        self.secured = True
        self.path = "/cloudconfig"
        self.manager = '/services/Cloud Manager'
        self.security_manager = '/services/Security Manager'
        super(CloudConfigurator, self).__init__(*args, **kw)
    def configure(self, config):
        self.secured = as_boolean(as_internal_node("/services").secured)
        self.setattr('path', config.get('path',self.path))
        self.setattr('manager', config.get('manager','/services/Cloud Manager'))
        super(CloudConfigurator, self).configure(config)
    def configuration(self):
        config = super(CloudConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['manager'] = self.getattr('manager')
        config['secured'] = str(int(self.secured))
        return config
    def stop(self):
        if not isinstance(self.manager, str):
            self.manager.dispatcher.unregister(self.sub)
            self.manager = as_node_url(self.manager)
        if not isinstance(self.security_manager, str):
            self.security_manager = as_node_url(self.security_manager)
        return super(CloudConfigurator, self).stop()
    def get_manager(self):
        manager = self.manager
        if self.secured:
            manager = self.security_manager.as_secured_node(manager)
        return manager
    def match(self, path):
        return path.startswith(self.path)
    def start(self):
        self.manager = self.nodespace.as_node(self.manager)
        self.security_manager = as_node(self.security_manager)
        self._pdo = PersistentDataObject(self)
        msg='The CloudConfigurator Persistent Object is in the file :%s' %str(self._pdo.filename())
        msglog.log('CloudConfigurator', msglog.types.INFO,msg)
        if os.path.exists(self._pdo.filename()):
            # Migration 
            msglog.log('CloudConfigurator', msglog.types.INFO, 'PDO Migration in Progress')
            self._pdo.formation = cPickle.dumps(IPickles(self.manager.formation))
            self._pdo.load()
            formation = IPickles(cPickle.loads(self._pdo.formation))()
            msglog.log('CloudConfigurator', msglog.types.INFO, 'PDO Migration for the Formation:%s' %str(formation))
            self.manager.update_formation(formation,None)
            self._pdo.destroy()
            del(self._pdo)
            msglog.log('CloudConfigurator', msglog.types.INFO, 'PDO Migration is Complete')           
        return super(CloudConfigurator, self).start()

    def get_node_names(self):
        formation = self.manager.get_formation()
        norm_formation=self.manager.nformation.normalize_formation(formation)
        ind=norm_formation.index(self.manager.peer)

        # move the peer to be at the head of the list
        p=formation.pop(ind)
        formation.insert(0,p)

        #insert manager at the very first place
        portal=self.manager.get_portal()
        if(portal == None):
            formation.insert(0,"")
        else:
            formation.insert(0,portal)
        return (formation)
 
    def validate(self,name):
        name=name.strip()
        if ( not (valid_ip_address(name) or valid_hostname(name))):
            return(1)
        if(name == 'localhost' ):
            return(1)
        if(name == '127.0.0.1' ):
            return(1)
        
        return(0)
    
    def handle_request(self, request):
        pass

        
    #create_node: name - name of the peer/portal
    #config - type = config["type"] string will tell if this is a "Peer" or a "Portal"
    def create_node(self, name, config=()):
        config = dict(config)
        type = config['type'].lower()
        manager = self.get_manager()
        # Next statements verify access to modifier permitted.
        if type == "peer":
            manager.add_peer
        else:
            manager.set_portal
        config.setdefault("parent", self.manager)
        peer_or_portal = config.setdefault("name", name).strip()
        ret = self.validate(peer_or_portal)
        if(ret != 0 ):
            msg='Add Peer/Portal failed. %s is a invalid hostname/IP Address' %(peer_or_portal)
            raise ValueError(msg)
        if(valid_hostname(peer_or_portal)):
            tmp=get_ip_addr(peer_or_portal)
            if(not valid_ip_address(tmp) ):
                raise ValueError('Cannot resolve the hostname %s. Please try with a valid Hostname' %(peer_or_portal))
        if(type == 'peer'):
            peer=peer_or_portal
            if (self.manager.is_peer_in_formation(peer) == False):
                if(self.manager.is_host_the_portal(peer) == False):
                    msg='Adding %s as a Peer' %str(peer)
                    msglog.log('CloudConfigurator', msglog.types.INFO,msg)
                    # Use possibly secured reference for the add.
                    manager.add_peer(peer)
                else:
                    raise ValueError,'A Portal cannot be a Peer : "%s" is the Portal for the Cloud.' % peer
            else:
                raise ValueError,'Add peer did nothing: "%s" already in Cloud Formation.' % peer
        else:
            portal=peer_or_portal
            if(self.manager.is_host_the_portal(portal) == False):
                if (self.manager.is_peer_in_formation(portal) == False):
                    msg='Setting the Portal as :%s' %str(portal)
                    msglog.log('CloudConfigurator', msglog.types.INFO,msg)
                    # Use possibly secured reference for the modification.
                    manager.set_portal(portal)
                else:
                    raise ValueError,'%s is in the formation. It cannot be added as Portal ' % portal
            else:
                raise ValueError,'Set Portal did nothing: "%s" already the Portal' % portal
        return(peer_or_portal)

    #remove_node: First check if name is manager then check in peer list to delete
    def remove_node(self, name):
        manager = self.get_manager()
        formation=self.manager.get_formation()
        if( name in formation ):
            msg='Removing %s as a Peer' %str(name)
            msglog.log('CloudConfigurator', msglog.types.INFO,msg)
            manager.remove_peer(name)
        else:
            msg='Removing %s as a Portal' %str(name)
            msglog.log('CloudConfigurator', msglog.types.INFO,msg)
            manager.set_portal(None)
        return name

