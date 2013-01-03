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
from SOAPpy import WSDL, Types
from mpx.lib.node import CompositeNode
from mpx.lib.configure import get_attribute,set_attribute,REQUIRED

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
		def __init__(self,name,target):
			self.__type_mask = []
			self.__name = name
			self.__target = target
		def append_type(self,param_type):
			self.__type_mask.append(param_type)
		def __call__(self,*args,**keywords):
			args = map(_type_conversion,self.__type_mask,args)
			results = getattr(self.__target,self.__name)(*args,**keywords)
			return Types.simplify(results)
	def configure(self,config):
		# For authentication wsdl file location attribute
		#   must be of http://username:password@etc...
		set_attribute(self,'wsdl','/var/mpx/config/PSS2WS.wsdl',config)
		return CompositeNode.configure(self,config)
	def configuration(self):
		config = CompositeNode.configuration(self)
		get_attribute(self,'wsdl',config)
		return config
	def start(self):
		self.__proxy = WSDL.Proxy(self.wsdl)
		for name,method in self.__proxy.methods.items():
			bound_function = self._NamedProxyFunction(name,self.__proxy)
			setattr(self,name,bound_function)
			# Setup function type mask with conversions or None for each param
			for param in method.getInParameters():
				bound_function.append_type(_type_map.get(str(param.type[1])))
		return CompositeNode.start(self)
	def stop(self):
		proxy = self.__proxy
		self.__proxy = None
		for operation in proxy.methods.keys():
			delattr(self,operation)
		return CompositeNode.stop(self)


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


