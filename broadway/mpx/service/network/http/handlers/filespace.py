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
import os
from threading import Event
from mpx.lib import msglog
from mpx.lib.node import as_node, as_internal_node
from mpx.componentry import implements
from mpx.componentry.security.declarations import secured_by
from mpx.componentry.security.declarations import SecurityInformation
from mpx.lib.exceptions import EAttributeError
from mpx.lib.neode.interfaces import IConfigurableNode
from mpx.lib.neode.interfaces import ICompositeNode
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute
from mpx.lib.configure import as_boolean
from mpx.service.network.http.request_handler import FileRequestHandler

class NodeLike(object):
    def as_node_url(self):
        return self.manager.makepath(self.manager.url, self.parent_path, self.name)
    url = property(as_node_url)
    def as_node(self, *args):
        return self
    def configuration(self):
        return {'name': self.name, 'parent': self.parent.as_node_url()}
    def _get_parent(self):
        parent = self.manager.make_parent(self.parent_path)
        return IConfigurableNode(parent)
    parent = property(_get_parent)
    def hasattr(self, attr):
        return hasattr(self, attr)
    def getattr(self, attr):
        return getattr(self, attr)
    def setattr(self, attr, value):
        return setattr(self, attr, value)
    def has_method(self, name):
        if hasattr(self, name):
            return callable(getattr(self, name))
        return 0
    def get_method(self, name):
        try: return self._get_method(name)
        except:
            msglog.exception()
            raise
    def _get_method(self, name):
        if hasattr(self, name):
            method = getattr(self, name)
            if callable(method):
                return method
            raise EAttributeError(
                "%r on %r not callable" % (name, self.__class__.__name__))
        raise EAttributeError("%r has no %r" % (self.__class__.__name__, name))

class DirectoryChild(NodeLike):
    implements(ICompositeNode)

    def __init__(self, manager, path, name):
        self.manager = manager
        self.parent_path = path
        self.name = name
    def children_names(self):
        return self.manager.children_names(self.parent_path, self.name)
    def children_nodes(self):
        return self.manager.children_nodes(self.parent_path, self.name)
    def get_child(self, name):
        return self.manager.get_child(name, self.parent_path, self.name)
    def has_child(self, name):
        return self.manager.has_child(name, self.parent_path, self.name)
    def prune(self):
        raise TypeError('Directory nodes cannot be deleted.')

class FileChild(NodeLike):
    implements(IConfigurableNode)

    security = SecurityInformation.from_default()
    security.protect_get('openread', 'View')
    security.protect_get('openwrite', 'Configure')
    security.disallow_set('name')
    security.disallow_set('parent_path')
    security.disallow_set('url')
    secured_by(security)

    def __init__(self, manager, path, name):
        self.manager = manager
        self.parent_path = path
        self.name = name
        self._path = self.manager.makepath(self.parent_path, self.name)
    def openread(self, mode = 'rb'):
        if '+' in mode or 'w' in mode:
            raise ValueError('Cannot pass "w" or "+" to openread.')
        return self.manager._filesystem.open(self._path, mode)
    def openwrite(self, mode = 'wb'):
        return self.manager._filesystem.open(self._path, mode)
    def prune(self):
        return self.manager._filesystem.unlink(self._path)

class FileSpace(FileRequestHandler):
    ignored = ("/public")
    def __init__(self, *args):
        self.__started = Event()
        self._security_manager = None
        self.provides_security = False
        self.public_resources = ("public/", "cues/", "dojoroot/")
        super(FileSpace, self).__init__(*args)
    def configure(self, config):
        set_attribute(self, 'node_browsable', True, config, as_boolean)
        self.secured = as_boolean(as_internal_node("/services").secured)
        super(FileSpace, self).configure(config)
    def configuration(self):
        config = super(FileSpace, self).configuration()
        get_attribute(self, 'node_browsable', config, str)
        get_attribute(self, 'secured', config, str)
        return config
    def start(self):
        super(FileSpace, self).start()
        if self.secured:
            self._security_manager = as_node('/services/Security Manager')
            self.provides_security = True
        self.__started.set()
    def stop(self):
        self.__started.clear()
        self.provides_security = False
        self._security_manager = None
        super(FileSpace, self).stop()
    def children_names(self, *parts):
        names = []
        if self.node_browsable:
            if self.__started.isSet():
                names = os.listdir(self.makepath(self.server_root, *parts))
        else:
            names = super(FileSpace, self).children_names()
        return names
    def children_nodes(self, *parts):
        if self.node_browsable:
            children = self.__children_nodes(*parts)
            if False and self.secured and len(children):
                count = len(children)
                as_secured = self._security_manager.as_secured_node
                as_node = NodeLike.as_node
                children = map(
                    as_secured, children, [None] * count, [as_node] * count)
        else:
            children = super(FileSpace, self).children_nodes()
        return children
    def __children_nodes(self, *parts):
        names = self.children_names(*parts)
        relative = self.makepath(*parts)
        children = [self._make_node(relative, name) for name in names]
        return children
    def get_child(self, name, *parts):
        if self.node_browsable:
            child = self.__get_child(name, *parts)
            if False and self.secured:
                as_secured = self._security_manager.as_secured_node
                child = as_secured(child, None, child.as_node)
        else:
            child = super(FileSpace, self).get_child(name)
        return child
    def __get_child(self, name, *parts):
        original = name
        name, path = self.__breakup_name(name)
        if path:
            parts = parts + (path,)
        if self.debug:
            message = 'File Space: get_child("%s") => get_child("%s", %s)'
            msglog.log('broadway', msglog.types.DB,
                       message % (original, name, parts))
        relative = self.makepath(*parts)
        names = self.children_names(relative)
        if name not in names:
            raise KeyError(name)
        return self._make_node(relative, name)
    def __breakup_name(self, name):
        path = ''
        if '/' in name:
            original = name
            index = name.rfind('/')
            if index > 1:
                path = name[0:index]
            name = name[index + 1:]
        return name, path
    def has_child(self, name, *parts):
        if self.node_browsable:
            name, path = self.__breakup_name(name)
            if path: parts += (path,)
            return self.__has_child(name, *parts)
        return super(FileSpace, self).has_child(name)
    def __has_child(self, name, *parts):
        relative = self.makepath(*parts)
        names = self.children_names(relative)
        return name in names
    def make_parent(self, path):
        if not path:
            return self
        else:
            if path and path[-1] == '/':
                path = path[0:-1]
            index = path.rfind('/')
            if index >= 0:
                parentpath = path[0:index]
                parentname = path[index + 1:]
            else:
                parentpath = ''
                parentname = path
            return self._make_node(parentpath, parentname)
    def makepath(self, *parts):
        parts = filter(None, parts)
        if not parts: return ''
        else: return os.path.join(*parts)
    def _make_node(self, path, name):
        nodeurl = self.makepath(self.url, path, name)
        absolute = self.makepath(self.server_root, path, name)
        if os.path.isdir(absolute):
            node = DirectoryChild(self, path, name)
        else:
            node = FileChild(self, path, name)
        return node
    def _process_securely(self, operation, path, request, *args, **kw):
        if not self.secured:
            # If not using security model, fallback to super's implementation.
            return super(FileSpace, self)._process_securely(
                operation, path, request, *args, **kw)
        # Security supplied by adapter supplying secured nodes.
        return operation(path, request, *args, **kw)
    def _process_file_read(self, path, request):
        if self.secured and not path.startswith(self.public_resources):
            if not request.authenticated():
                return request.authenticate()
        return super(FileSpace, self)._process_file_read(path, request)
    def _openread(self, path, mode = 'rb'):
        if not self.secured or path.startswith(self.public_resources):
            return super(FileSpace, self)._openread(path, mode)
        child = self.get_child(path)
        as_secured = self._security_manager.as_secured_node
        child = as_secured(child, None, child.as_node)
        return child.openread(mode)
    def _openwrite(self, path, mode = 'wb'):
        if not self.secured or path.startswith(self.public_resources):
            return super(FileSpace, self)._openwrite(path, mode)
        try: 
            child = self.get_child(path)
        except KeyError:
            name, path = self.__breakup_name(path)
            child = self._make_node(path, name)
        as_secured = self._security_manager.as_secured_node
        child = as_secured(child, None, child.as_node)
        return child.openwrite(mode)
    def as_node_url(self, *args):
        return super(FileSpace, self).as_node_url(*args)
    url = property(as_node_url)

