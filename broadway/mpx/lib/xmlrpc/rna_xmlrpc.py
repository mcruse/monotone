"""
Copyright (C) 2002 2003 2004 2007 2009 2010 2011 Cisco Systems

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
import StringIO
import base64
import traceback
import types
import uu
import xml.parsers.expat

from mpx.lib.node import as_node, as_node_url, as_internal_node
from mpx.service import ServiceNode
from mpx.lib.configure import Iterator
from mpx.lib.xmlrpc import XMLRPC_ObjectInterface
from mpx.lib.exceptions import EInvalidSession
from mpx.lib.exceptions import MpxException
from mpx.lib.exceptions import Unauthorized
from mpx.lib import msglog, BinaryString
from mpx.service.subscription_manager import SUBSCRIPTION_MANAGER
from mpx.service.session import ESessionDenied
from mpx.service.security.user import User as User

# Handle a single RNA request via XMLRPC
class RNA_XMLRPC_Handler(object):
  ##
  # Create a session manager object to create sessions
  # @todo use as_node to load from running service
  def __init__(self):
    self._manager = None
    self._subscriptions = {}
    self._qualified_method_list = {}
    self._services = {}
    self._methods = {}
    return

  def _as_node(self, nodeurl, *args):
      return as_node(nodeurl, *args)

  def _as_node_url(self, node, *args):
      return as_node_url(node, *args)

  def manager(self):
    if self._manager is None:
      self._manager = as_internal_node('/services/session_manager')
    return self._manager
  ##
  # Invoke the RNA call.
  #  @param service  The 'node' to find
  #  @param method   The method on Node to call
  #  @param *args the arguments for the node
  #               The first argument MUST be a valid SessionID
  #
  #  @return Depends on the call.
  #  @throws EInvalidSession on invalid session
  #
  def invoke(self, sessionID, service, method, *args):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')

    s = self._as_node(service)
    a = getattr(s, method)

    ## Check to see if any of the args have been UUEncoded
    ## If so, decode them here..
    cnt=-1
    args_new = []
    args_new.extend( args )

    for ar in args_new:
      cnt = cnt + 1
      if type(ar) == types.StringType:
        if ar.startswith('begin '):      # is uuencoded
          infile =  StringIO.StringIO(ar)
          outfile = StringIO.StringIO()
          uu.decode(infile, outfile )
          args_new[cnt] = outfile.getvalue()

    result = apply(a, args_new)

    if isinstance(result,BinaryString):
      # This is the legacy ConfigTool specific base64 encoding.
      return ''.join(("<encode type='base64'>",
                      base64.standard_b64encode(result),
                      "</encode>"))

    return result


  ## Invoke the RNA command for each argument
  #  @param args is a list of delimited rna requests in the form
  #              of SERVICE:METHOD (/interfaces/counter1:get)
  #  @returns tuple of results  -- one for each.  On exception
  #            the error is logged in proper slot
  #
  def invoke_batch(self, sessionID, *args):
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    results = []
    for rna in args:
      # since we are spliting on ":" I put in a place holder
      # for the mpx:// before I do a split the put it back after
      # since mpx:// has a ":"
      rna = rna.replace ("mpx://",'$$PLACE_HOLDER$$')
      rna_s = rna.split(':')
      service = rna_s[0].replace('$$PLACE_HOLDER$$','mpx://')
      method = rna_s[1]
      try:
        result = self.invoke(sessionID, service, method)
        results.append(result)
      except Exception, e:
        results.append(self._exception_string(e))
    return results

  ##
  # The friendly thing to do...
  def cancel_batch_async(self, sessionID):
    if self._subscriptions.has_key(sessionID):
        try:
          subscription = self._subscriptions[sessionID]
          del self._subscriptions[sessionID]
          del self._qualified_method_list[sessionID]
          del self._services[sessionID]
          del self._methods[sessionID]
          SUBSCRIPTION_MANAGER.destroy(subscription)
        except:
          msglog.log('RNA_XMLRPC_Handler',msglog.types.WARN,
                     "Error destroying subscription %r." % (subscription,))
          msglog.exception()
    return

  ##
  # Create a new subscription where the caller intends to poll for the
  # values.
  #
  # @param node_reference_table An optional dictionary of node references
  #                             keyed by NIDs (the client specific, node
  #                             identifier) used as the initial
  #                             subscription.
  # @timeout An optional timeout specified in seconds.  If the subscription
  #          is not polled within TIMEOUT seconds, then the subscription
  #          will be destroyed.
  # @default 60 seconds.
  # @return The SID (subscription identification) used to uniquely identify
  #         the subscription.
  def subscription_create_polled(self, sessionID,
                                 node_reference_table=None, timeout=60.0):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.create_polled(node_reference_table, timeout)
  ##
  # Destroy an existing subscription.
  # @param sid The subscription id returned by <code>new_subscription</code>.
  def subscription_destroy(self, sessionID, sid):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.destroy(sid)
  ##
  # Add new node references and replace existing node references from a
  # dictionary.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  # @param node_reference_table A dictionary of node references keyed by
  #                             NIDs (the client specific, node identifier).
  def subscription_merge(self, sessionID, sid, node_reference_table):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.merge(sid, node_reference_table)
  ##
  # Completely replace a subscription's node reference table.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  # @param node_reference_table A dictionary of node references keyed by
  #                             NIDs (the client specific, node identifier).
  def subscription_replace(self, sessionID, sid, node_reference_table):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.replace(sid, node_reference_table)
  ##
  # Remove all entries from a subscription's node reference table.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  def subscription_empty(self, sessionID, sid):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.empty(sid)
  ##
  # Add a new entry to the subscription's node reference table.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  # @param nid The Node ID that will identify the new node reference.
  # @param node_reference A Node Reference for the Node to add to the
  #                       subscription's  node reference table.
  def subscription_add(self, sessionID, sid, nid, node_reference):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.add(sid, nid, node_reference)
  ##
  # Modify an existing entry in the subscription's node reference table.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  # @param nid The Node ID that will identify the new node reference.
  # @param node_reference A Node Reference for the Node to add to the
  #                       subscription's  node reference table.
  def subscription_modify(self, sessionID, sid, nid, node_reference):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.modify(sid, nid, node_reference)
  ##
  # Remove a specific node reference from a subscription's node reference
  # table.
  #
  # @param sid The subscription id returned by <code>new_subscription</code>.
  # @param nid The Node ID used that identifies the specific node reference
  #            to remove.
  def subscription_remove(self, sessionID, sid, nid):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.remove(sid, nid)
  ##
  # Poll the subscription service for all subscribed Node's whose values have
  # changed since the last time <code>poll_changed</code> was invoked or
  # since the subscription was created, which ever is more recent.
  #
  # @param sid The id of the subscription to poll for changes.  This is the
  #            'handle' that was returned by create_polled.
  # @return A dictionary, keyed by the Node ID of the changed values "result
  #         dictionary".  The "result dictionary" dictionary has three
  #         keys: "value", "timestamp" and "cached".  The "value" key returns
  #         the actual value read from the Node, or the exception that
  #         prevented reading a value.  The "timestamp" key returns that best
  #         estimate as to when the value was read, as a float of seconds
  #         since 1970, UTC.  And "cached" is a boolean that is false if it
  #         is guaranteed that the value was not returned from a cache.
  def subscription_poll_changed(self, sessionID, sid):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.poll_changed(sid)
  ##
  # Poll the subscription service for all subscribed Node's.
  #
  # @param sid The id of the subscription to poll for changes.  This is the
  #            'handle' that was returned by create_polled.
  # @return A dictionary, keyed by the Node ID of the Node's "result
  #         dictionary".  The "result dictionary" dictionary has three
  #         keys: "value", "timestamp" and "cached".  The "value" key returns
  #         the actual value read from the Node, or the exception that
  #         prevented reading a value.  The "timestamp" key returns that best
  #         estimate as to when the value was read, as a float of seconds
  #         since 1970, UTC.  And "cached" is a boolean that is false if it
  #         is guaranteed that the value was not returned from a cache.
  #         If the subscription service has not received an initial value for
  #         the node, then None is returned for that Node instead of a
  #         "result dictionary."
  def subscription_poll_all(self, sessionID, sid):
    # Raise exception if this is not a valid session
    if not self.manager().validate(sessionID, touch=1):
      raise EInvalidSession('Invalid session')
    return SUBSCRIPTION_MANAGER.poll_all(sid)
  ##
  # Invoke the RNA command for each argument, building a subcription
  # for the session.
  #
  #  @param *args is a list of delimited rna requests in the form
  #         of NODE:METHOD (/interfaces/counter1:get)
  #  @returns tuple of results  -- one for each.  On exception
  #           the error is logged in proper slot
  #
  # @todo Support non-get methods.
  def invoke_batch_async(self, sessionID, *qualified_method_list):
    subscription = None
    if not self.manager().validate(sessionID, touch=1):
      if self._subscriptions.has_key(sessionID):
        try:
          subscription = self._subscriptions[sessionID]
          del self._subscriptions[sessionID]
          del self._qualified_method_list[sessionID]
          del self._services[sessionID]
          del self._methods[sessionID]
          SUBSCRIPTION_MANAGER.destroy(subscription)
        except:
          msglog.log('RNA_XMLRPC_Handler',msglog.types.WARN,
                     "Error destroying subscription %r on stale session %r." %
                     (subscription, sessionID))
          msglog.exception()
      raise EInvalidSession('Invalid session')

    if self._subscriptions.has_key(sessionID):
      subscription = self._subscriptions[sessionID]
      if (self._qualified_method_list[sessionID] != qualified_method_list):
        # New batch, destroy the out of date subscription.
        try:
          del self._subscriptions[sessionID]
          del self._qualified_method_list[sessionID]
          del self._services[sessionID]
          del self._methods[sessionID]
          SUBSCRIPTION_MANAGER.destroy(subscription)
        except:
          msglog.log('RNA_XMLRPC_Handler',msglog.types.WARN,
                     "Error destroying previous subscription %r." %
                     (subscription,))
          msglog.exception()
        subscription = None

    if subscription is None:
      #
      # No subscription matching the batch, create one!
      # Build a node_reference_table:
      subscription_map = {}
      services = []
      methods = []
      for i in range(0,len(qualified_method_list)):
        rna = qualified_method_list[i]
        i_method = rna.rfind(':')
        if i_method == -1 or (i_method == 3 and rna[:3] == "mpx"):
          # There is no method specified.
          rna_node = rna
          rna_method = ''
        else:
          rna_node = rna[:i_method]
          rna_method = rna[i_method+1:]
        services.append(rna_node)
        methods.append(rna_method)
        if methods[i] == 'get':
          subscription_map[services[i]] = services[i]
      # Create the subscription using the genereated node_reference_table:
      subscription = SUBSCRIPTION_MANAGER.create_polled(subscription_map,
                                                        5*60.0)
      self._subscriptions[sessionID] = subscription
      self._qualified_method_list[sessionID] = qualified_method_list
      self._services[sessionID] = services
      self._methods[sessionID] = methods
      #
      # Now that we've added our node's, validate the other sessions.
      #
      validate_list = []
      validate_list.extend(self._subscriptions.keys())
      for test_session in validate_list:
        if not self.manager().validate(test_session, touch=0):
          expired = None
          try:
            expired = self._subscriptions[test_session]
            del self._subscriptions[test_session]
            del self._qualified_method_list[test_session]
            del self._services[test_session]
            del self._methods[test_session]
            SUBSCRIPTION_MANAGER.destroy(expired)
          except:
            msglog.log('RNA_XMLRPC_Handler',msglog.types.WARN,
                       "Error destroying subscription %r on stale session %r." %
                       (expired, test_session))
            msglog.exception()
    # Get all 'ready' values.
    services = self._services[sessionID]
    methods = self._methods[sessionID]
    polled_values = SUBSCRIPTION_MANAGER.poll_all(subscription)
    results = []
    for i in range(0,len(services)):
      service = services[i]
      try:
        if methods[i] == 'get':
          result = polled_values[service]
          if result is None:
              result = 'error: Waiting for update...'
          else:
              result = result['value']
          if isinstance(result,Exception):
            result = self._exception_string(result)
        else:
          result = 'error: %r method not supported, only get().' % (
            methods[i]
            )
        results.append(result)
      except Exception, e:
        results.append(self._exception_string(e))
    return results
  def _exception_string(self,e):
    _print_exc_str = getattr(e,'_print_exc_str',None)
    if not _print_exc_str:
      s = StringIO.StringIO()
      traceback.print_exc(None,s)
      s.seek(0)
      _print_exc_str = s.read()
      del s
      if hasattr(e,'_print_exc_str'):
        e._print_exc_str = _print_exc_str
    return 'error: %s.%s%r\n%s' % (e.__class__.__module__,
                                   e.__class__.__name__,
                                   e.args,
                                   _print_exc_str)
  ## Create a new session for the user and password
  #  @param user The user name
  #  @param password The password for the user
  #  @returns A string that identifies the session
  def create_session(self, user, password=None):
      if isinstance(user, User): username = user.name
      else: username = user
      try:
        session_id = self.manager().create(user, password)
        return session_id
      except ESessionDenied, error:
        raise Unauthorized('Session denied for "%s": %s' % (username, str(error)))
      except Exception, e:
        msglog.log('broadway',msglog.types.WARN,
                    "RNA_XMLRPC_Handler: Could not create session for %r,%r" %
                   (username, password))
        msglog.log('broadway',msglog.types.ERR,"RNA_XMLRPC_Handler: %s" % e)
        raise Exception('Error creating new session: %s' % str(e))
    
  def destroy_session(self, sid):
    try:
      destroyed = self.manager().destroy(sid)
    except:
      msglog.log('broadway',msglog.types.WARN,
                 "RNA_XMLRPC_Handler: failed to destroy %r" % sid)
      raise
    return destroyed

  ## Return nodes with that have named method
  #  @param method The name of the method that each node should have
  #  @return tuple of nodes that have method
  #
  def get_nodes_with_method(self, method):
    matches = []
    root = self._as_node('/')
    i = Iterator(root)
    while i.has_more():
      n = i.get_next_node()
      if hasattr(n, method):
        matches.append( self._as_node_url(n) )

    return matches
  def get(self, skipCache=0):
    return 'RNA via XMLRPC 1.0'

class SecuredXmlRpcHandler(RNA_XMLRPC_Handler):
    def __init__(self, *args):
        msglog.log('broadway', msglog.types.DB, 'Initialized Secured XML RPC Handler')
        super(SecuredXmlRpcHandler, self).__init__(*args)
        self._security_manager = None
    
    def __get_sm(self):
        if self._security_manager is None:
            self._security_manager = as_node('/services/Security Manager')
        return self._security_manager
    security_manager = property(__get_sm)

    def _as_node(self, nodeurl, *args):
        return self.security_manager.as_secured_node(nodeurl, *args)

    def create_session(self, *args):
        user=None
        password=None
        if len(args) == 2:
            user, password = args
            msglog.log('broadway', msglog.types.WARN,
                       'Deprecated create_session with '
                       'explicit password being used.')
        else:
            if len(args) == 1:
                try: user = self.security_manager.user_manager.get_user(args[0])
                except KeyError:
                    msglog.exception(prefix = 'Handled')
                    raise ValueError('Invalid user name: %s' % args[0])
            else:
                user = self.security_manager.user_manager.user_from_current_thread()
        return super(SecuredXmlRpcHandler, self).create_session(user, password)

class SecuredXmlRpcHandler2(SecuredXmlRpcHandler):
    def __init__(self,encode_type='base64'):
        msglog.log('broadway', msglog.types.DB, 'Initialized Secured XML RPC Handler 2')
        self._encode_type=encode_type
        super(SecuredXmlRpcHandler2, self).__init__()
        self._encoder_mgr = _EncodingManager()
        return

    def invoke(self, sessionID, service, method, *args):
        if not self.manager().validate(sessionID, touch=1):
            raise EInvalidSession('Invalid session')
        s = self._as_node(service)
        a = getattr(s, method)

        ## Check to see if any of the args have been encoded
        ## If so, decode them here..
        cnt=-1
        args_new = []
        args_new.extend( args )

        for ar in args_new:
            cnt = cnt + 1
            if type(ar) == types.StringType:
                if ar.startswith('<encode'): # is encode
                    args_new[cnt] = self._decode(ar)  # decode string

        ## Make the low-level call
        result=None
        result = apply(a, args_new)

        if isinstance(result, types.StringType):
            encode=0
            if isinstance(result, BinaryString):
              encode=1
            elif result.find('>>]') > -1:
               encode=1

            if encode:
              result = self._encoder_mgr.encode(result, self._encode_type)
            # all strings are in CDATA sections
            result = '<![CDATA[' + result + ']]>'
        return result

    ## Decode the String encoded by type
    #   @param type The type of encoding the string used
    #  @returns Decoded string
    #  @throws MpxException if any error occurs during decoding
    def _decode(self,orig):
        try:
            result = self._encoder_mgr.decode(orig)  ## get value from XML
        except Exception, e:
            raise MpxException('Error while decoding value "%s"' % str(e))
        return result
    def _encode(self, value, encode_type='base64'):
        return self._encoder_mgr.encode(value, encode_type)




## Class RNA_XMLRPC_Handler2 provides RNA over XMLRPC
#  with the added ability to encode any strings with
#  a settable encoder/decoder.
#
#  If an argument has been encoded it is marked with
#  '++encode:Base64++df8729s9929343'  Which would
#  mean to decoding using Base64 The value df8729s9929343.
#  I'm sure we can come up with better taging ...
class RNA_XMLRPC_Handler2(RNA_XMLRPC_Handler):

    def __init__(self,encode_type='base64'):
        self._encode_type=encode_type
        RNA_XMLRPC_Handler.__init__(self)
        self._encoder_mgr = _EncodingManager()
        return


    ## To allow for String types to be encoded they need to
    #  to have the token ++encode:TYPEOFENCODE++ set as the
    #  start of the string.  This is not XML, but a token
    #  before the data.  This is to not force an XML document
    #  to need to be created for each check.
    #
    def invoke(self, sessionID, service, method, *args):
        ##Raise exception if this is not a valid session

        if not self.manager().validate(sessionID, touch=1):
            raise EInvalidSession('Invalid session')

        s = self._as_node(service)
        a = getattr(s, method)

        ## Check to see if any of the args have been encoded
        ## If so, decode them here..
        cnt=-1
        args_new = []
        args_new.extend( args )

        for ar in args_new:
            cnt = cnt + 1
            if type(ar) == types.StringType:
                if ar.startswith('<encode'): # is encode
                    args_new[cnt] = self._decode(ar)  # decode string

        ## Make the low-level call
        result=None
        result = apply(a, args_new)

        if isinstance(result, types.StringType):
            encode=0
            if isinstance(result, BinaryString):
              encode=1
            elif result.find('>>]') > -1:
               encode=1

            if encode:
              result = self._encoder_mgr.encode(result, self._encode_type)
            # all strings are in CDATA sections
            result = '<![CDATA[' + result + ']]>'
        return result

    ## Decode the String encoded by type
    #   @param type The type of encoding the string used
    #  @returns Decoded string
    #  @throws MpxException if any error occurs during decoding
    def _decode(self,orig):
        try:
            result = self._encoder_mgr.decode(orig)  ## get value from XML
        except Exception, e:
            raise MpxException('Error while decoding value "%s"' % str(e))
        return result
    def _encode(self, value, encode_type='base64'):
        return self._encoder_mgr.encode(value, encode_type)


## class _EncodingManager is used to encapsulate
#  the handling of encoding for XMLRPC RNA requests.
#  It implments all the encoding processed for encoding
#  and decoding.
class _EncodingManager(object):
    def __init__(self):
        self._encode_type = None
        self._encoded_val = None
        self._encode_type = None
        #
        self._encode_parser = xml.parsers.expat.ParserCreate()
        self._encode_parser.StartElementHandler = self._start_element
        self._encode_parser.EndElementHandler = self._end_element
        self._encode_parser.CharacterDataHandler = self._char_data
        return
    ## Encode the String in type encoding
    #  @param type The type of encoding the string to use
    #  @returns Encoded string preceded by the ENC_TOK type ENC_TOK_END
    #           for example.   ++encode:base64++F(#KD(#D(#D(#KD
    #   @throws MpxException if any error occurs during encoding
    def encode(self,orig,encode_type='base64'):
        try:
            newval = None
            if encode_type == 'base64':
                newval = base64.encodestring(orig)
            else:
                raise MpxException('Unsupported encoding type "%s"' %
                                   encode_type)
            return '<encode type="%s">%s</encode>' % (encode_type,newval)
        except Exception, e:
            raise MpxException('Error while encoding value "%s"' % str(e))

    ## decode the encoded_value.  First parse the XML and
    #  and decode with encode_type in encode.type
    #
    def decode(self, encoded_value):
        try:
            self._encoded_val = ''
            self._encode_type = ''
            self._encode_parser.Parse(encoded_value)
            decoded_val = ''
            if self._encode_type == 'base64':
                decoded_val = base64.decodestring(self._encoded_val)
            else:
                raise MpxException('Unknown encode type "%s"' %
                                   self._encode_type)
            return decoded_val
        except Exception, e:
            raise MpxException('Error decoding string: %s' % str(e))




    def _start_element(self, name, attrs):
        self._encode_type = attrs['type']

    def _end_element(self, name):
        pass

    def _char_data(self, data):
        self._encoded_val = self._encoded_val + data
