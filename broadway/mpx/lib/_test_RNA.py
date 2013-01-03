"""
Copyright (C) 2001 2010 2011 Cisco Systems

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

from testing.fixtures.default import DefaultTestFixture


from mpx.lib.rna_xml import ProtocolInterfaceImplXML
from mpx.lib.rna_xml import RNARequestImplXML, _InvokeResultFromXML
from mpx.lib.rna import StringTransport, SimpleTextProtocol
from mpx.service.network.rna import RNAHeader, _invoke_command

import array

    
 
class TestRNA(DefaultTestFixture):
  
  
  ## @returns Text of test XML request
  def _getRequestText(self):
    requestText = '<?xml version="1.0"?><SbRequest  service="/services/configuration" token="None" request="INVOKE" method="read"><SbArgumentList><arg_1 type="string"><![CDATA[Test Arg1]]></arg_1><arg_0><![CDATA[Test Arg_0]]></arg_0></SbArgumentList></SbRequest>'
    return requestText
  
  def _getRequestTextRepr(self):
    requestText = "{'token': 'None', 'args': '(\"This is an argument\")', 'method': 'read_nodedef_db', 'service': '/services/configuration'}"
    return requestText
  
  ## Test the creation of a XML RNA request and 
  #  check to make sure it returns the appropriate things
  #
  def test_RNA_CreateRequestWithArguments(self):
    
    request = RNARequestImplXML(self._getRequestText())
    assert(request.get_method() == 'read')    
    assert(request.get_service() == '/services/configuration')
    assert(request.get_argument_list()[1] == 'Test Arg1') 
    

  ## Test the creation of a empty request.  
  def test_RNA_CreateRequestEmpty(self):
    request = RNARequestImplXML('<SbRequest/>')
    
    assert(len(request.get_arguments()) == 0)
    
    
  ## Test creating an XML Protocol
  def test_RNA_CallXMLProtocol(self):
      
    transport = StringTransport()
    transport.buffer = array.array('c', self._getRequestText())
    header = RNAHeader(None, len( self._getRequestText() ))
    protocol = ProtocolInterfaceImplXML(transport, header)
    
    c = protocol.recv_command()
    
    assert(c.method == 'read')
    assert(c.service == '/services/configuration')
    assert(c.get_arguments() != '()')
           
           
    

  ## Test creating a SimpleTextProtocol and make
  #  the arguments are as expected
  def test_RNA_CallSimpleTextProtocol(self):
    
    transport = StringTransport()
    transport.buffer = array.array('c', self._getRequestTextRepr())
    header = RNAHeader(None, len( self._getRequestTextRepr() ))
    protocol = SimpleTextProtocol(transport, header)
    
    c = protocol.recv_command()
    
    assert(c.method == 'read_nodedef_db')
    assert(c.service == '/services/configuration')
    assert(c.get_arguments() != '')
    
    
  def test_RNA_XMLCommandException(self):
    
    e = Exception()
    r = _InvokeResultFromXML()
    s = r.formatException(e)
    
    assert(s == 'exceptions.Exception')
    
    
from testing.test_manager import test
if(__name__ == '__main__'):    
  test(TestRNA, 1)

  
  



    
      
       
    
    
  
