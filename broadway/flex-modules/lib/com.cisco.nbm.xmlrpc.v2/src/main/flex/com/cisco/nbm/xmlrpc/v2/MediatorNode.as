///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import com.cisco.nbm.xmlrpc.v2.calls.GetMediatorNodesCall;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	
	import mx.events.PropertyChangeEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	
	/**
	 * This class represents a node in the mediator.  
	 * 
	 * You can execute basic methods on the node like children_nodes and
	 * children_names.  Some of the nodes on the mediator have additional methods
	 * based on their specialization, and we could made the mediator node
	 * a dynamic object on which you could call random methods but this would
	 * prevent us from catching certain errors and it would be difficult to
	 * properly parse the result.  Therefore, in order to add specialized nodes, 
	 * the user can ask the mediator service to use a certain class that extends 
	 * this class with additional methods.
	 * 
	 * Later versions may allow the user to update the node type on the service
	 * so that cached nodes are replaced with their specialized nodes.
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 */
	public class MediatorNode extends EventDispatcher implements IMediatorNode
	{
		/**
		 * The path to the node on the mediator.
		 */
		private var _path:String;
		
		/**
		 * The call factory to create calls.  Usually, the service.
		 */
		private var _callFactory:IMediatorNodeCallFactory;
		
		private var _cachedResults:Object = {};
		
		private var _cachedChildren:Array = null;
		
		private var _lastChildrenCached:int = 0;
		
		private var _service:XMLRPCService;
		
		private var _name:String;

		private var _id:String;
		
		private var _config:Object;
		
		// Flag that indicates if the node can handle children_names ...
		private var _handlesChildrenNames:Boolean;

		private static const logger:ILogger = Log.getLogger("cisco.nbm.net.v2.MediatorNode");

		public function MediatorNode()
		{
			
		}
		
		public function getService():XMLRPCService
		{
			return _service;
		}
		
		// TODO Move to have configuration return cached configuration and then update 
		public function get configObject():Object
		{
			return _config;
		}
		
		// TODO rename
		/**
		 * Initialize the node
		 */
		public function init(service:XMLRPCService, name:String, path:String):void
		{
			logger.debug("init node: " + name + ", " + path);
			_service = service;
			_name = name;
			_path = path;
		}		
		
		public function get id():String
		{
			return _id;
		}
		
		public function get name():String
		{
			return _name;
		}

		public function getattr(attributeName:String):MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function hasattr(attributeName:String):MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function setattr(attributeName:String, value:*):MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function configure(params:Object):MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function configuration():MediatorNodeCall
		{
			var call:MediatorNodeCall = createMediatorNodeCall("configuration");
			call.addEventListener(Event.COMPLETE, handleConfigurationComplete);
			
			return call;
		}
		
		private function handleConfigurationComplete(event:Event):void
		{
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
			
			cleanupCall(call, [ Event.COMPLETE, handleConfigurationComplete ]);
			
			var result:Object = call.result;
			logger.debug("result: " + result);
			dumpRawConfiguration(result);
			
			_config = result;
			updateFromConfiguration();
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "configObject", null, _config));
		}
		
		private function updateFromConfiguration():void
		{
			setId(_config["__node_id__"]);
			setEnabled(_config["enabled"]);
			setName(_config.name);
		}
		
		private function setName(value:String):void
		{
			if (value != _name)
			{
				var oldValue:String = _name;
				_name = value;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "name", oldValue, _name));
			}
		}
		
		private function setEnabled(value:Boolean):void
		{
			// _enabled = value;
			//dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "enabled", oldValue, true));
		}
		
		private function dumpRawConfiguration(config:Object):void
		{
			logger.debug("**** DUMP RAW CONFIG [" + this + "] ****");
			for (var key:String in config)
			{
				logger.debug("'"+key+"'='"+config[key]+"'");
			}
			logger.debug("**** END DUMP RAW CONFIG ****");
		}
		
		private function setId(value:String):void
		{
			if (_id != value)
			{
				var oldValue:String = _id;
				_id = value;
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "id", oldValue, _id));
			}
		}
		
		protected function cleanupCall(call:MediatorNodeCall, ... eventTypeHandler):void
		{
			for each (var tuple:Array in eventTypeHandler)
			{
				logger.debug("cleaning: " + tuple[0] + ", " + tuple[1]);
				call.removeEventListener(tuple[0], tuple[1]);
			}
		} 
		
		public function start():MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function stop():MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function has_child(name:String):MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function get_child(name:String):MediatorNodeCall
		{
			return createMediatorNodeCall("get_child", [name]);
		}
		
		public function children_nodes():MediatorNodeCall
		{
			var call:MediatorNodeCall = callFactory.createCall(this, "children_names", [], GetMediatorNodesCall);
			
			return call;
		}
		
		public function execute(methodName:String, args:Array):MediatorNodeCall
		{
			return createMediatorNodeCall(methodName, args);
		}
		
		public function refresh():void
		{
			if (_cachedChildren != null)
			{
				for each (var child:IMediatorNode in _cachedChildren)
				{
					child.destroy();
				}
			}
			
			_cachedChildren = null;
			// force retrieval of children
			var o:Object = children;
		}
		
		public function get children():Array
		{
			if (_cachedChildren == null)
			{
				_cachedChildren = [];
				var call:MediatorNodeCall = createMediatorNodeCall("children_names");
				call.addEventListener(Event.COMPLETE, handleGetChildrenComplete);
				call.addEventListener(ErrorEvent.ERROR, handleGetChildrenError);		
			}
			
			return _cachedChildren;
		}
		
		private function handleGetChildrenComplete(event:Event):void
		{
			logger.debug("get children complete: " + event + ", on path " + _path);
			
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
			//call.removeEventListener(Event.COMPLETE, handleGetChildrenComplete);
			cleanupCall(call, [ Event.COMPLETE, handleGetChildrenComplete ],
					[ErrorEvent.ERROR, handleGetChildrenError]);
			
			var result:Array = call.result as Array;
			
			if (_cachedChildren.length > 0)
			{
				_cachedChildren.splice(0, _cachedChildren.length);
				
				// need to remove from children and dispose of them.  
				// Potentially lengthy operation ...?
			}
			
			if (result.length == 0)
			{
				// If we set this to null then it continues to call get children
				//_cachedChildren = null;
			}
			
			for each (var nodeName:String in result)
			{
				logger.debug("got > '" + nodeName + "'");
				var childPath:String = _path + "/" + nodeName;
				//var childPath:String = _path + nodeName;
				 logger.debug("\tCalling for child path: " + childPath);
				var newChild:IMediatorNode = _service.getNode(childPath);
				newChild.configuration();
				
				_cachedChildren.push(newChild); 
			}
			
			
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _cachedChildren));
		}
		
		private function handleGetChildrenError(event:ErrorEvent):void
		{
			logger.error("!!!!!!!!Error while calling get children: " + event.text);
		}
		
		public function set children(value:Array):void
		{
			throw new Error("'children' is a read-only property");
		}
		
		public function children_names():MediatorNodeCall
		{
			throw new Error("Not implemented");
			return null;
		}
		
		public function get_value():MediatorNodeCall
		{
			return createMediatorNodeCall("get");
		}
		
		protected function createMediatorNodeCall(name:String, args:Array=null):MediatorNodeCall
		{
			// TODO Attach as listener
			return _callFactory.createCall(this, name, args);
		}
		
		public function set_value(value:*):MediatorNodeCall
		{
			return _callFactory.createCall(this, "set", value);
		}
		
		// Attributes
		public function get path():String
		{
			return _path;
		}
		
		public function get callFactory():IMediatorNodeCallFactory
		{
			return _callFactory;
		}
		
		public function set callFactory(value:IMediatorNodeCallFactory):void
		{
			_callFactory = value;
		}
		
		override public function toString():String
		{
			return "[MediatorNode(path='"+_path+"', name='"+_name+"']";
		}
		
		public function setPath(value:String):void
		{
			var oldPath:String = _path;
			_path = value;
			// update children path
			
			// Take the new path and update the name
			var possibleName:String = value.substring(value.lastIndexOf("/")+1)
			
			if (possibleName != _name)
			{
				setName(possibleName);
			}
			
			
			if (_cachedChildren != null)
			{
				for each (var child:IMediatorNode in _cachedChildren)
				{
					var childPath:String = child.path;
					var newChildPath:String = "";
					newChildPath = _path + childPath.substr(oldPath.length);
					child.setPath(newChildPath);
				}
			}
		}
		
		public function destroy():void
		{
			if (_cachedChildren != null)
			{
				for each (var child:IMediatorNode in _cachedChildren)
				{
					child.destroy();
				}
			}
		}
		
		public function internalAddChild(newChild:MediatorNode):void
		{
			if (_cachedChildren == null)
			{
				_cachedChildren = [];
			}
			_cachedChildren.push(newChild); // TODO There could be a problem here where the children are duplicated ...
			dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, _cachedChildren));
		}
	}
}