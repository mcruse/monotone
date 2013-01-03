"""
Copyright (C) 2008 2010 2011 Cisco Systems

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
from SOAPpy import WSDL
from SOAPpy import Types
from SOAPpy.Types import faultType

from mpx.lib.node import CompositeNode
from mpx.lib.node import as_node
from mpx.lib.node import is_node_url

from mpx.lib.configure import REQUIRED
from mpx.lib.configure import set_attribute
from mpx.lib.configure import get_attribute

from mpx.lib.exceptions import EConfigurationInvalid

from moab.linux.lib.uptime import secs as now

# Map of types that do not encode/decode natively in 2.2

_type_map = {'boolean': Types.booleanType,
             'string':str, 'str':str,
             'int': int, 'integer': int,
             'float': float}
# Function takes conversion (or None) and value.
#   returns value as is if conversion is None, otherwise conversion(val)
def _type_conversion(conversion,value):
    if conversion is None: return value
    return conversion(value)

class RemoteWebServiceProxy(CompositeNode):        
    class _NamedProxyFunction:
        def __init__(self, name, target):
            self.__type_mask = []
            self.__name = name
            self.__target = target
            return
            
        def append_type(self, param_type):
            self.__type_mask.append(param_type)
            
        def __call__(self,*args, **keywords):
            args = map(_type_conversion,self.__type_mask,args)
            results = getattr(self.__target, self.__name)(*args, **keywords)
            return Types.simplify(results)
            
    def configure(self, cd):
        # For authentication wsdl file location attribute
        #   must be of http://username:password@etc...
        set_attribute(self,'wsdl', REQUIRED, cd)
        return super(RemoteWebServiceProxy, self).configure(cd)
        
    def configuration(self):
        cd = CompositeNode.configuration(self)
        get_attribute(self,'wsdl', cd)
        return cd
        
    def start(self):
        self._proxy = WSDL.Proxy(self.wsdl)
        for name, method in self._proxy.methods.items():
            bound_function = self._NamedProxyFunction(name, self._proxy)
            setattr(self, name, bound_function)
            # Setup function type mask with conversions or None for each param
            for param in method.getInParameters():
                bound_function.append_type(_type_map.get(str(param.type[1])))
        return super(RemoteWebServiceProxy, self).start()
        
    def stop(self):
        proxy = self._proxy
        self._proxy = None
        for operation in proxy.methods.keys():
            delattr(self, operation)
        return super(RemoteWebServiceProxy, self).stop()
            
class RemoteWebServiceOp(CompositeNode):
    class SOAPCallParams(dict):
        def __call__(self, o, inparams):
            named_args = []
            for param in inparams:
                if isinstance(o, CompositeNode):
                    named_args.append((param.name, o.param.get()))
                else:
                    named_args.append((param.name, o.param))
            self.update(dict(named_args))
            return self.copy()
            
    def __init__(self, *args):
        super(RemoteWebServiceOp, self).__init__(*args)
        self.__call_args_r = None
        self.__call_args_w = None
        self._last_value = None
        self._last_rcvd_at = now()
        return
                
    def configure(self, cd):
        super(RemoteWebServiceOp, self).configure(cd)
        set_attribute(self, 'ttl', 60, cd, int)
        set_attribute(self, 'read_op', '', cd)
        set_attribute(self, 'read_params', [], cd)
        set_attribute(self, 'write_op', '', cd)
        set_attribute(self, 'write_params', [], cd)
        return
        
    def configuration(self):
        config = CompositeNode.configuration(self)
        get_attribute(self, 'ttl', cd)
        get_attribute(self, 'read_op', cd)
        get_attribute(self, 'read_params', cd)
        get_attribute(self, 'write_op', cd)
        get_attribute(self, 'write_params', cd)
        return cd
        
    def start(self):
        self._do_read = getattr(self.parent, self.read_op)
        if self.write_op:
            self._do_write = getattr(self.parent, self.write_op)
            setattr(self, 'set', self._set)
            self.inparams_write = self.parent._proxy.methods[self.write_op].inparams
            for parameter in self.write_params:
                if hasattr(self.__call_args_w, name):
                    raise EConfigurationInvalid(name)
                if value.startswith('/') and is_node_url(value):
                    setattr(self.__call_args_w, name, as_node(value))
                else:
                    setattr(self.__call_args_w, name, value)
        self.inparams_read = self.parent._proxy.methods[self.read_op].inparams
        for parameter in self.read_params:
            if not self.__call_args_r:
                self.__call_args_r = object()
            name = parameter['pn']
            value = parameter['value']
            if hasattr(self.__call_args_r, name):
                raise EConfigurationInvalid(name)
            if value.startswith('/') and is_node_url(value):
                setattr(self.__call_args_r, name, as_node(value))
            else:
                setattr(self.__call_args_r, name, value)
        return super(RemoteWebServiceOp, self).start()
            
    def get(self, skipCache=0):
        if self._last_value and (now() - self._last_rcvd_at) < self.ttl:
            return self._last_value
        if self.__call_args_r:
            value = self._do_read(
                **self.SOAPCallParams(
                    self.__call_args_r, self.inparams_read
                )
            )
        else:
            value = self._do_read()
        self._last_rcvd_at = now()
        self._last_value = value
        return self._last_value
        
    def _set(self, value):
        if self.__call_args_w:
            self._do_write(
                **self.SOAPCallParams(
                    self.__call_args_w, self.inparams_write
                )
            )
        else:
            self._do_write()
        return
        
if __name__ == '__main__':
    # license,query,start,maxResults,filter,restrict,safeSearch,lang_restrict
    arguments=('XIpnd2FQFHL0FG8JO/9sLIVn2yj/X++W',
                'spotted owl',0,10,False,'',False,'','','')
                
    def test_google(proxy,query='spotted owl',args=arguments):
        return proxy.doGoogleSearch(args[0],query,*(args[2:]))
        
    def print_results(results):
        for i in range(len(results['resultElements'])):
            title = results['resultElements'][i]['title']
            noh_title = title.replace('<b>', '').replace('</b>', '')
            print 'title: ' + noh_title
            print '  url: ' + results['resultElements'][i]['URL'] + '\n'

    def setup_google_wsdl(query='spotted owl'):
        rwsp = RemoteWebServiceProxy()
        rwsp.configure({'wsdl':'http://api.google.com/GoogleSearch.wsdl',
                        'name':'google','parent':'/services'})
        rwsp.start()
        return rwsp
        
    
	
