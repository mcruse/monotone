"""
Copyright (C) 2001 2002 2010 2011 Cisco Systems

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
## rna_xml -- RNA Using XML 
#
#  This module contains code to implement ProtocolInterface as
#  an XML file.  The XML is used to encapsulate the RNA request
#  as a series of XML tokens/attributes.
#
#  Given a service, method and it's arguments you can construct an
#  XML representation for transfer as in the following:
#
#  NOTE: the 'type' attribute associated with the argument.  We currently
#  support 'string','float','integer' and 'long' types
#  Also note, that the 'encode' attribute allows for 'pre-request' encoding
#  of results.   This enables sending of binary data (ZIP Files, images ...)
# <code>
#
#
#  <SbRequest token='SECURITY' service='/services/configuration' method='read' encode='uuenode'
#       <ArgumentList>
#            <Config type='text'>
#                <![CDATA[<MpxConfig version='33434'><node ..........
#            </Config>
#            <ConfigMode type='integer'>
#               12
#            </ConfigMode>
#       </ArgumentList>
#  </SbRequest>
#
#
# </code>
#  
#  The command will be process on the server and the results sent back as follows:
#
#  <code>
#
#
# <SbServerReply status='OK|FAILED' >
#     <data>
#        <![CDATA[And Data From Servce]]>
#    </data>
#    <message>
#        <![CDATA[Any Message (exception) From Service]]>
#    </message>
# </SbServerReply>
#
# </code>
#
# If an exception occurrs the 'Message' is filled in with any relavent information
# and the Status is set to FAILED.  Otherwise, the status is 'OK' and the 'Data' contains
# the results of the command.
# NOTE: The formating of the exception is handled via _MessageBase#formatException.  This method 
# is overridden in _InvokeCommandFromXML.
#
#
#@todo Refine the XML DTD to allow for greater flexibility.  Perhaps implement XML-RPC.

import array
import types
import traceback
import string
import StringIO
import uu
from mpx.lib.exceptions import ENotImplemented, EInvalidCommand, EInvalidMessage
from mpx.lib.rna import ProtocolInterface, _InvokeCommand, _InvokeResult
from xml import sax


## Interface RNARequestInterface
# @notes Defines an interface to abstract the 
#        different pieces of info needed to execute
#        an RNA request
#
class RNARequestInterface:
  
  ## Return the service this RNA request is for
  def get_service(self):
    raise ENotImplemented
  
  ## Return the method on the server to call
  def get_method(self):
    raise ENotImplemented
  
  ## return the encode type the client is excpecting
  def get_encode(self):
    raise ENotImplemented
    
  ## Return any arguments needed by the call
  def get_arguments(self):
    raise ENotImplemented
  

## Class _InvokeCommandFromXML 
#  @notes Invoke RNA call from an XML request
class _InvokeCommandFromXML(_InvokeCommand):
  

  
  def __init__(self, header):
    _InvokeCommand.__init__(self, header)

    self.request = None

  def pack(self):
    pass
  
  def unpack(self):
     
     self.request = RNARequestImplXML( self.buffer.tostring() )
     
     self.service = self.request.get_service()
     self.method = self.request.get_method()
     self.encode = self.request.get_encode()
     
     
  ##
  # Get message out of transport and store in buffer.
  #
  # @param recv  Transport to get message out of.
  # @param timeout  Time to await reply before timing
  #                 out.
  #
  def fromtransport(self,recv,timeout):
    buffer = array.array('c')
    
    recv(self.header.len, timeout, buffer)
    self.buffer = buffer
     
  ##
  # Format the execption for the client.  This should format
  # the exception in such a way the client will be able to understand
  # the type of exception, and any related messages associated with it
  #
  # @param e The exception object
  # @param args Any arguments associated with Exception
  # @param tbo The Trace Back Object
  def formatException(self, e, args, tbo):

    if type(e) == types.StringType:
      e = Exception(e)
    elif type(e) == types.ClassType:
      e = args
      args = ""
    
    listTb = traceback.format_tb( tbo )
    
    exception = "'%s' in module '%s' with arguments '%s' Trace --> %s" % (str(e.__class__), str(e.__module__), str(args), str(listTb))
    
    # Documenation says to remove this reference otherwise, a 
    # circular references occurs.
    listTb = None
    
    
    return exception
 

  ##
  # Return a tuple that represents the argments needed for this command
  def get_arguments(self):
    return self.request.get_argument_list()
  
  
##
# Holds result from a method
# invocation message.
# The result is encapsulated in XML in pack()
# 
# @implements ProtocolResult
#
class _InvokeResultFromXML(_InvokeResult):
    CMD = 'RESULT'
    SERIVCE_KEY = 'service'
    METHOD_KEY = 'method'
    RESULT_KEY = 'result'
    EXCEPTION_KEY = 'exception'
    
    END_OF_CDATA_TOKEN = "+++END_OF_CDATA+++"

    def __init__(self):
        self.service = None	# '/services/logger'
        self.method = None	# 'get_range'
        self.result = None	# Result string 
        self.exception = None   # an exception...
 

    ##
    # Package a result for sending.
    #
    # @param command  the Command object to contains the request
    # @param result  String representation of result, will be
    #                evaluated.
    # @param exception  String representation of any exception
    #                   that may have ocurred while invoking
    #                   the command.
    #
    # @see _BaseMessage#pack
    #

    def pack(self,command,result): # Exception!
      self.service = command.service
      self.method = command.method
      self.result = result
      self.exception = result.exception
      self.command = command
      
      if(self.exception != '' and self.exception != 'None'):
        status = "FAILED"
      else:
        status = 'OK'
      
      ## if type is not a String, then we UUEncode it
      #  and the receiver will decode.
      
      dataResult = result.result
      
      if self.command.encode:
        print "Encoding data ..."
        infile =  StringIO.StringIO(dataResult)
        outfile = StringIO.StringIO()
        uu.encode( infile, outfile )
        dataResult = outfile.getvalue()
        
        ## we Need to replace any ]]> chars with special marker
        ## to avoid screwing up the XML CDATA section
        if dataResult.find(']]>') > -1:
          print 'Check complete'
          dataResult = string.replace(dataResult, ']]>', self.END_OF_CDATA_TOKEN)
          
        
      resultXML = "<SbServerReply status='%s' ><data><![CDATA[%s]]></data><message><![CDATA[%s]]></message></SbServerReply>" % (status, dataResult, self.exception)
      
      resultHeader = 'XML:RESULT:%07d' % len(resultXML)
      
      self.buffer = array.array('c', resultHeader + ':' + resultXML)
      
    ##
    # Unpack a result that has been received and
    # store values in self.
    #
    # @see _BaseMessage#unpack
    #
    def unpack(self):
      pass

    
##    
    
    
    
class ProtocolInterfaceImplXML(ProtocolInterface):
  
  ##
  # @see ProtocolInterface#__init__
  #
  def __init__(self, transport=None, header=None):
     ProtocolInterface.__init__(self, transport, header)
    
  ##
  # Get a string representation of this object.
  #
  # @return String representation of this object.
  def __repr__(self):
    return 'mpx.lib.rna.ProtocolInterfaceImplXML(%s)' % self.transport
  
  ##
  # @see #__repr__
  #
  def __str__(self):
    return self.__repr__()
  
  ##
  # @see ProtocolInterface#send_command
  #
  def send_command(self,command):
    raise ENotImplemented
  
  ##
  # @see ProtocolInterface#recv_command
  #
  def recv_command(self):
    c = _InvokeCommandFromXML(self.header)
    c.fromtransport(self.transport.recv,-1)
    c.unpack()
    return c
  
  
  ##
  # @see ProtocolInterface#send_result
  #
  def send_result(self,command,result):
    r = _InvokeResultFromXML()
    r.pack(command, result)
    r.totransport(self.transport.send)
    
    
  
  ##
  # @see ProtocolInterface#recv_result
  #
  def recv_result(self):
    raise ENotImplemented
  
    

## Class RNARequestImplXML encapsulate a
#  single RNA request from XML.
#  Each RNA transaction has a RNARequest associated with it.
# @implements RNARequestInterface
#
class RNARequestImplXML(RNARequestInterface):
  
  
  parser = None
  
  def __init__(self, xmlText):
    self.parser = _RNARequestXMLParser(xmlText)
  
  def get_service(self):
    return self.parser.get_attribute('service')
  
  def get_method(self):
    return self.parser.get_attribute('method')

  ## return the encode type expected by client
  def get_encode(self):
    return self.parser.get_attribute("encode")
  
  def get_arguments(self):
    return self.parser.get_arguments()

  ## return a list of arguments sorted by argument name
  def get_argument_list(self):
    args = self.parser.get_arguments()
    
    keys = args.keys()    
    
    keys.sort()
    argList = []
    for key in keys:
      argList.append( args[key] )
      
    return argList
  

##
# XML DOM parser for the RNA XML Requests
# 
class _RNARequestXMLParser(sax.ContentHandler):
  
  ## Create parser, and use ourself as 
  #  the content handler for this string
  
  def __init__(self, xmlText):
    self.arguments = {}
    self.attributes = {}
    self.buffer = ""

    self._argumentStart = 0
    self._argumentKeyCurrent = None
    self._argumentTypeCurrent = None

    sax.parseString(xmlText, self)
    

  def get_attribute(self, name):
    if self.attributes.has_key(name):
      return self.attributes[name]
    else:
      return None
    
  

  def get_attributes(self):
    return self.attributes
    

  def get_arguments(self):
    return self.arguments
  
    
  ##
  # Called by xml_parser when document ends.
  #
  def endDocument(self):
    pass
  
  ##
  # Called by xml_parser when an opening tag is encountered.
  #
  # @param name  Name of the tag opened.
  #
  # @param attrs  <code>xml attr</code> object containing
  #               attributes enclosed in opening tag.
  #
  def startElement(self, name, attrs):
    if(name == 'SbRequest'):
      self.attributes = attrs  # The attributes associated with this request

    elif (name == 'SbArgumentList'):
      self._argumentStart = 1
      
    elif (self._argumentStart == 1):
      ## add element as an argument to the current list
      self._argumentKeyCurrent = name
      if attrs.has_key('type'):
        self._argumentTypeCurrent = attrs['type']
      else:
        self._argumentTypeCurrent = None        
      
      self.buffer = ""

      
  def endElement(self, name):
    if name == 'SbRequest':
      pass
    elif name == 'SbArgumentList':
      pass
    elif self._argumentStart == 1:
      
      ## assume end of an attribute
      value = convert_rna_arg_to_type(self.buffer, self._argumentTypeCurrent)

      self.arguments[self._argumentKeyCurrent] = value
      
      
      self._argumentStart = 0
      self._argumentKeyCurrent = None
      self.buffer = ""
      
  
        
  def characters(self, data):
    if(self._argumentStart == 1):
      self.buffer += data
                          
    

## Convert value of String type to type identified by type
#@param data The data of string type that will be converted
#@param type An token that identifies the type.   The token is 
#       is either 'string' or 'number'.  The RNA client sets the 
#       appropriate type of the value.
#@returns The value of the type defined in argType.  
#         if a string, then it is striped.
import string

def convert_rna_arg_to_type(data, argtype):
  if type == 'string':
    pass
  elif argtype == 'integer':
    data = string.atoi(data)
  elif argtype == 'float':
    data = string.atof(data)

  if type(data) == types.StringType or type(data) == types.UnicodeType:
    data = string.strip(data)
    
  return data

  