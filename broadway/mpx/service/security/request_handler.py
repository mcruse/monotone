"""
Copyright (C) 2007 2008 2009 2010 2011 Cisco Systems

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
import time
import string
import urllib
import cPickle
import re
from threading import Lock
from HTMLgen import HTMLgen
from mpx.lib import msglog
from mpx.lib.node import as_internal_node
from mpx.lib.configure import as_boolean
from mpx.componentry.interfaces import IPickles
from mpx.lib.neode.node import CompositeNode
from mpx.service.network.http.response import Response
from mpx.www.w3c.xhtml.interfaces import IWebContent
from mpx.lib.persistent import PersistentDataObject
from mpx.service.garbage_collector import GC_NEVER
from mpx.service.alarms2.trigger.triggers import Trigger
from mpx.service.alarms2.trigger.triggers import ComparisonTrigger
from role import Role
from user import User
from policy import Policy
from moab.user import manager as _manager
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.lib.exceptions import Unauthorized

def valid_username(request, username):
    error_message = _manager.valid_username(username)
    if error_message:
        request.error(403, error_message)
        msglog.log('broadway', msglog.types.INFO, error_message)
        return False
    return True

def valid_password(request, username, password, admin):
    error_message = _manager.valid_password(password, username, admin)    
    if error_message:
        # since request has been given an error resp
        request.error(403,error_message)
        msglog.log('broadway', msglog.types.INFO, error_message)
        return False
    return True

def valid_administrator(request, user):
    # get minimim admin password length from moab
    cfg = _manager.password_config
    cfg = _manager.password_config
    pw_min_len_admin = cfg.getint('Length', 'minadmin')
    if len(user.password) < pw_min_len_admin:
        error_message = 'System Administrator password ' \
           'must be longer than %d characters.\n\r' \
           'Change password & Commit' % \
           (pw_min_len_admin)
        request.error(403, error_message)
        msglog.log('broadway', msglog.types.INFO, error_message)
        return False
    return True

class SecurityConfigurator(CompositeNode):
    LOADFAILURE = '"%s" failed to load %s "%s".  Exception follows.'
    security = SecurityInformation.from_default()
    secured_by(security)

    def __init__(self, *args):
        self._pdo_lock = Lock()
        super(SecurityConfigurator, self).__init__(*args)
    def configure(self, config):
        self.setattr('path', config.get('path','/securityconfig'))
        self.setattr('manager', config.get('manager','/services/Security Manager'))
        self.secured = as_internal_node("/services").secured
        super(SecurityConfigurator, self).configure(config)
    def configuration(self):
        config = super(SecurityConfigurator, self).configuration()
        config['path'] = self.getattr('path')
        config['manager'] = self.getattr('manager')
        config['secured'] = str(self.getattr('secured'))
        return config
    def start(self):
        self.manager = self.nodespace.as_node(self.manager)
        
        self._pdo_lock.acquire()
        try:
            self._pdo = PersistentDataObject(self, dmtype=GC_NEVER)
            self._pdo.users = {}
            self._pdo.roles = {}
            self._pdo.policies = {}
            self._pdo.load()
            userdumps = self._pdo.users.items()
            roledumps = self._pdo.roles.items()
            policydumps = self._pdo.policies.items()
        finally: self._pdo_lock.release()
        super(SecurityConfigurator, self).start()

        tstart = time.time()
        for rolename, roledump in roledumps:
            try: IPickles(cPickle.loads(roledump))()
            except:
                message = self.LOADFAILURE % (self.name, 'role', rolename)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Security Configurator loaded '
                   '%s roles in %s seconds.' % (len(roledumps), tlapse))

        tstart = time.time()
        for policyname, policydump in policydumps:
            try: IPickles(cPickle.loads(policydump))()
            except:
                message = self.LOADFAILURE % (self.name, 'policy', policyname)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Security Configurator loaded '
                   '%s policies in %s seconds.' % (len(policydumps), tlapse))

        tstart = time.time()
        for username, userdump in userdumps:
            try: IPickles(cPickle.loads(userdump))()
            except:
                message = self.LOADFAILURE % (self.name, 'user', username)
                msglog.log('broadway', msglog.types.ERR, message)
                msglog.exception(prefix = 'Handled')
        tend = time.time()
        tlapse = tend - tstart
        msglog.log('broadway', msglog.types.INFO,
                   'Security Configurator loaded '
                   '%s users in %s seconds.' % (len(userdumps), tlapse))
        return
    def stop(self):
        super(SecurityConfigurator, self).stop()
        self.manager = None
    def match(self, path):
        return path.startswith(self.path)
    
    security.protect('_create_child', 'Manage Users')
    def _create_child(self, childtype, parent, config = {}):
        count = 0
        namebase = "New %s %d"
        child = parent.nodespace.create_node(childtype)
        default = {'parent': parent, 'description': ''}
        default.update(config)
        while True:
            if not config.has_key("name"):
                default["name"] = namebase % (childtype.__name__, count)
            try: 
                child.configure(default)
            except ValueError, error:
                # If failed over 20 times, assume error in logic and
                #   exit loop.  Also re-raise exception if name specified.
                if count > 20 or config.has_key('name'): 
                    raise
                else: 
                    count += 1
            except Exception, e:
                child.prune()
                raise
            else: 
                break
        return child

    def handle_request(self, request):
        try:
            response = Response(request)
            request_data = request.get_post_data_as_dictionary()
            request_data.update(request.get_query_string_as_dictionary())
            context = request_data['manager'][0]
            adapt = self.__handle_by_context(context, request, request_data)
            if adapt is not None:
                # Since password rejection completes request...
                webadapter = IWebContent(adapt)
                response['Content-Type'] = "text/html"
                response.send(webadapter.render(self.path))
            return
        except Unauthorized, e:
            request.error(403, "Permission Denied: %s"%e)
        except Exception, e:
            request.error(400, "%s"%e)

    def __handle_by_context(self, context, request, data):
        contextlookup = {'roles': (self.manager.role_manager,
                                   Role, self._pdo.roles),
                         'users': (self.manager.user_manager,
                                   User, self._pdo.users),
                         'policies': (self.manager.policy_manager,
                                      Policy, self._pdo.policies)}
        managernode, childtype, pdodict = contextlookup[context.lower()]
        if self.secured:
            manager = self.manager.as_secured_node(managernode)
        else:
            manager = managernode
        adapt = manager
        affected=[]
        affected.append(context)
        if data.has_key("node"):
            name = urllib.unquote_plus(data['node'][0])
            node = manager.get_child(name)
            adapt = node
        else:
            node = None
        if data.has_key("actionName"):
            action = urllib.unquote_plus(data['actionName'][0])
            if action == "configure" or action == "add":
                config = {}
                for fieldname in data.keys():
                    prefix,sep,attrname = fieldname.partition('.')
                    if sep and prefix == "configure":
                        values = map(urllib.unquote_plus, data[fieldname])
                        if attrname.endswith("password"):
                            if len(values) == 2:
                                if values[0] != values[1]:
                                    request.error(403,"Passwords did not match")
                                    return None                                    
                        config[attrname] = values[0]
                
                if managernode is self.manager.user_manager:
                    if action == "add":
                        adminrole = False
                        if 'roles' in config.keys() and config['roles'] == 'System Administrator':
                            adminrole = True
                            config['roles'] = ['System Administrator']
                        username = password = ""
                    elif node:
                        username = node.name
                        
                        password = node.password
                        adminrole = 'System Administrator' in node.roles
                    else:
                        raise TypeError("configure action requires node")
                    username = config.get("name", username)
                    if not valid_username(request, username):
                        msglog.log("broadway", msglog.types.WARN,
                                   "username validation failed")
                        return
                    password = config.get("password", password)
                    if not valid_password(request, username, 
                                          password, adminrole):
                        msglog.log("broadway", msglog.types.WARN, 
                                   "Ignoring invalid user configuration")
                        return

                # Validate name. It should not allow space and should not be null.
                name = config.get("name",'')
                if re.match('^([^ ^(^)^\'^\,]*)$', name) == None:
                    request.error(403,'Space in name.')
                    return

                if action == "add":
                    manager.add_child
                    #name = config.get("name",'')
                    if name == '':
                        request.error(403,'No %s name specified'%childtype)
                        return
                    node = self._create_child(childtype, manager, config)
                    node.start()
                    adapt = node
                else:
                    try: 
                        node.stop()
                    except: 
                        msglog.exception(prefix='Handled')
                    old_config = node.configuration()
                    try:
                        node.configure(config)
                    except Exception, e:
                        node.configure(old_config)
                        msglog.log("broadway", msglog.types.INFO, 
                                   "Restarting '%s' with old configuration" % node.name)
                        node.start()
                        raise
                    try: 
                        node.start()
                    except: 
                        msglog.exception(prefix='Handled')
                    adapt = node
            elif action == "remove":
                if node is None:
                    raise TypeError("remove action requires node")
                if manager.hasattr("user_from_current_thread"):
                    if manager.user_from_current_thread().name == node.name:
                        raise Exception("Cannot delete self")
                temp=node.prune()
                if temp is not None: 
                    affected=temp   
                #capturing all changed items if multiple affected by remove
                #else prune returns None
                adapt = manager
            elif action == "invoke":
                if node is None:
                    raise TypeError("invoke action requires node")
                if not data.has_key("methodName"):
                    raise TypeError("invoke action requires methodName")
                methodname = urllib.unquote_plus(data.get('methodName')[0])
                # test for changing to System Administrator and make sure
                # password will meet length requirements
                params = map(urllib.unquote_plus, data.get('params', []))
                method = getattr(node, methodname)
                if methodname == 'set_roles':
                    if node.name == "mpxadmin" and "System Administrator" not in params:
                        request.error(403, 'mpxadmin user cannot be demoted')
                        return None
                    if node.name != "mpxadmin" and "System Administrator" in params:
                        if not valid_administrator(request, node):
                            return None
                result = method(*params)
            elif action != "edit":
                raise TypeError("Unknown action: %s" % action)
            update_pdo = True
        else:
            update_pdo = False
        if update_pdo:
            self.updatepdo(affected)
        if self.secured:
            adapt = self.manager.as_secured_node(adapt)
            adapt.test_adaptability()
        return adapt
    
    def updatepdo(self,affected):
        contextlookup = {'roles': (self.manager.role_manager,
                                   self._pdo.roles),
                         'users': (self.manager.user_manager,
                                   self._pdo.users),
                         'policies': (self.manager.policy_manager,
                                      self._pdo.policies)}
        for context in affected:
            managernode, pdodict = contextlookup[context.lower()]
            tstart = time.time()
            self._pdo_lock.acquire()
            try:
                pdodict.clear()
                children = managernode.children_nodes()
                for child in children:
                    pdodict[child.name] = cPickle.dumps(IPickles(child))
                self._pdo.save()
            finally: 
                self._pdo_lock.release()
            tend = time.time()
            tlapse = tend - tstart
            message = 'Security Configurator pickled and wrote '
            message += '%s nodes in %s seconds ' % (len(children), tlapse)
            message += 'for "%s".' % managernode.name
            msglog.log('broadway', msglog.types.INFO, message)
        
    