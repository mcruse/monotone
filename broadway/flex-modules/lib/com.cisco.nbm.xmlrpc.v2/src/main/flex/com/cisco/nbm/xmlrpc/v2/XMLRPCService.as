///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.net.URLLoader;
	import flash.net.URLLoaderDataFormat;
	import flash.net.URLRequest;
	import flash.net.URLRequestHeader;
	import flash.net.URLRequestMethod;
	
	import mx.logging.ILogger;
	import mx.logging.Log;
	import mx.utils.Base64Encoder;
	
	[Event(name="callComplete", type="com.cisco.nbm.xmlrpc.v2.XMLRPCServiceEvent")]
	[Event(name="error", type="flash.events.ErrorEvent")]
	
	/**
	 * The XMLRPC service acts as a factory for calls on a mediator.
	 * 
	 * The primary design considerations were the following:
	 * 
	 * <ul>
	 * 	<li>Configure credentials in one spot</li>
	 *  <li>Use weak references for callbacks</li>
	 *  <li>Based on the design of the mediator's RPC service instead of abstract 
	 * 		XML RPC</li>
	 * </ul>
	 * 
	 * Typical way of calling:
	 * 
	 * <code>
	 * var service:XMLRPCService = new XMLRPCService(host, "/XMLRPCv2", username, password);
	 * var node:IMediatorNode = service.getNode("/services/time");
	 * var token:AsyncToken = node.getValue();
	 * token.addResponder(this) // assumes this implements IResponder
	 * </code>
	 * 
	 * ... handle event in responder
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 * 
	 */
	public class XMLRPCService extends EventDispatcher implements IMediatorNodeCallFactory
	{
		/**
		 * Five seconds timeout default for network calls.  
		 * 
		 * If the timeout is reached before the call is finished
		 * executing then the call is considered to be an error.
		 */
		public static const DEFAULT_TIMEOUT_MS:int = 60 * 2 * 1000; 
		
		private var _rootURI:String;
		
		private var _username:String;
		
		private var _password:String;
		
		private var _address:String;
		
		private var _protocol:String = "http";
		
		private var _cachedAuthHeader:URLRequestHeader;
		
		private var logger:ILogger;
		
		/**
		 * Used to cache all mediator nodes
		 */
		private var nodeCache:Object = {};
		
		public static const VERSION:String = "1.0";
		
		/**
		 * Default timeout in milliseconds for a request.
		 */
		private var _timeoutMS:int = DEFAULT_TIMEOUT_MS;  
		
		/**
		 * Create and configure the XML-RPC service.
		 * 
		 * @param address The address to the service (can be the IP, or a hostname)
		 * @param rootURI The root to the XMLRPC service on the mediator, typically: /XMLRPCv2/RNA
		 * @param username The username to login with
		 * @param password The password to login with
		 * @param protocol Either http or https.  http by default.
		 */
		public function XMLRPCService(address:String, rootURI:String, username:String, password:String, protocol:String="http")
		{
			_address = address;
			_rootURI = rootURI;
			_username = username;
			_password = password;
			_protocol =  protocol != null ? protocol : null;//"http";
			
			logger = Log.getLogger("cisco.nbm.net.v2.XMPRPCService"); 
		}
		
		/**
		 * Updates the username and sets the auth header for subsequent calls.
		 */
		public function set username(value:String):void
		{
			if (_username != value)
			{
				_username = value;
				_cachedAuthHeader = null;
			}
		}
		
		public function set timeout(value:int):void
		{
			_timeoutMS = value;
		}
		
		/**
		 * Updates the password and set the auth header for subsequent calls.
		 */ 
		public function set password(value:String):void
		{
			if (_password != value)
			{
				_password = value;
				_cachedAuthHeader = null;
			}
		}
		
		/**
		 * Returns a node configured to path on the mediator configured for this service.
		 * 
		 * If the node type needs specialization, pass the class name as the nodeType.
		 * 
		 * Nodes are cached, so if a node at the path was configured then it is returned.
		 * 
		 * @param nodePath The path to the node on the mediator
		 * @param nodeType The type of node to create.  Use null to create a generic MediatorNode
		 * @return A configured node of IMediatorNode type.
		 * @throws Error If the nodeType is not of IMediatorNode
		 */
		public function getNode(nodePath:String, nodeType:Class=null):IMediatorNode
		{
			var nodeName:String = "";
			
			if (nodePath.lastIndexOf("/") >= 0)
			{
				nodeName = nodePath.substr(nodePath.lastIndexOf("/") + 1);
			}
			
			// NOTE Turning off cache
			/*
			if (nodeCache[nodePath] != null)
			{
				return nodeCache[nodePath];
			}
			*/
			
			var node:IMediatorNode = null;
			
			if (nodeType == null)
			{
				nodeType = MediatorNode;
			}
			
			node = new nodeType();
			node.init(this, nodeName, nodePath);
			
			// Node should be of IMediatorNode type
			if (!(node is IMediatorNode)) {
				throw new Error("nodeType must implement 'IMediatorNode'");
			} 
			
			node.callFactory = this;
			
			nodeCache[nodePath] = node;
			
			return node;
		}
		
		/**
		 * Create a node call that you can later execute.  This is used 
		 * internally by the mediator nodes but can also be used by the programmer
		 * to execute calls that the node class does not implement.  
		 * 
		 * For example, if the user has gotten a node that has a method called
		 * "create_schedule" and they wish to call that method they are unable 
		 * to execute the call on the node object itself because no such 
		 * method exists.  So, the user can call this method instead as follows:
		 * 
		 * var call:MediatorNodeCall = service.createCall( scheduleHolderNode,
		 * 		"create_schedule");
		 * call.addEventListener(Event.COMPLETE, handleCreateScheduleComplete);
		 * ... // additional handlers
		 * call.execute();
		 * 
		 * Finally, handle the result in the listener:
		 * 
		 * <code>
		 * function handleCreateScheduleComplete(event:Event):void
		 * {
		 * 		var call:MediatorNodeCall = event.target as MediatorNodeCall;
		 * 		var result:Object = call.result;
		 * 		.... // Do stuff with the result
		 *      // DON'T FORGET TO REMOVE YOURSELF AS A LISTENER!!!!
		 * 		call.removeEventListener(Event.COMPLETE, handleCreateScheduleComplete);
		 * } 
		 * </code>
		 * 
		 * @param node The node to execute the call on.
		 * @param name The method name.
		 * @param args Arguments passed to the method, or null to pass no arguments
		 * @param type The type of mediator node call.  If you pass node, then MediatorNodeCall is used. 
		 * @return A mediator node call that you can execute. 
		 */
		public function createCall(node:IMediatorNode, name:String, args:Array=null, type:Class=null):MediatorNodeCall
		{
			var call:MediatorNodeCall = null;
			
			if (type == null)
			{
				call = new MediatorNodeCall();//this, node, name, args);
			}
			else
			{
				call = new type();//this, node, name, args);
			}
			
			call.init(this, node ,name, _timeoutMS, args);
			
			var path:String = getPathToNode(node.path);
			
			
			logger.debug("creating call path at: " + node.path);
			var request:URLRequest = new URLRequest(path);
			
			request.method = URLRequestMethod.POST;
			
			var serializer:XMLRPCSerializer = new XMLRPCSerializer(name, args);
			
			request.data = serializer.serialize().toString();
			logger.debug(">> CALL STRING");
			logger.debug("'" + request.data + "'");
			
			if (_cachedAuthHeader == null && _username != null && _username.length > 0)
			{
				_cachedAuthHeader = createAuthHeader();
			}
			
			if (_cachedAuthHeader != null)
			{
				request.requestHeaders.push(_cachedAuthHeader);
			}
			
			var loader:URLLoader = new URLLoader();
			loader.dataFormat = URLLoaderDataFormat.TEXT;
			
			call.attachLoaderListeners(loader);
			
			attachCallListeners(call);
			call.execute(request);
			//call.addEventListener(MediatorNodeCallEvent.TIMEOUT, handleCallTimeout);
			//call.addEventListener(Event.COMPLETE, handleCallComplete);
			
			return call;
		}
		
		private function attachCallListeners(call:MediatorNodeCall):void
		{
			call.addEventListener(MediatorNodeCallEvent.TIMEOUT, handleCallTimeout);
			call.addEventListener(Event.COMPLETE, handleCallComplete);
		}
		
		private function removeCallListeners(call:MediatorNodeCall):void
		{
			call.removeEventListener(MediatorNodeCallEvent.TIMEOUT, handleCallTimeout);
			call.removeEventListener(Event.COMPLETE, handleCallComplete);
		}
		
		private function handleCallTimeout(event:MediatorNodeCallEvent):void
		{
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
			removeCallListeners(call);
			
			dispatchTimeoutError(call);
		}
		
		private function handleCallComplete(event:Event):void
		{
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
			removeCallListeners(call);
			
			dispatchEvent(new XMLRPCServiceEvent(XMLRPCServiceEvent.CALL_COMPLETE));
		}
		
		private function dispatchTimeoutError(call:MediatorNodeCall):void
		{
			var event:ErrorEvent = new ErrorEvent(ErrorEvent.ERROR);
			event.text = "Timeout error while making a network call '" 
				+ call.name + "' on node: '" + call.node.path + "'";
			dispatchEvent(event);
		}
		
		/*
		 *  Cache credentials
		 */
		private function createAuthHeader():URLRequestHeader
		{
			var encoder:Base64Encoder = new Base64Encoder();
			encoder.encode(_username + ":" + _password);
			
			return new URLRequestHeader("Authorization", "Basic " + encoder.toString());
		}
		
		/*
		 * Create a path to the node.  This is not used externally so the 
		 * visibility will change.
		 */
		public function getPathToNode(path:String):String
		{
			var fullPath:String = "";
			if (_protocol != null)
			{
				fullPath = _protocol;
			}
			
			if (_address != null)
			{
				fullPath += _address;
			}
			return fullPath + _rootURI + path;
		}
	}
}