///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import com.cisco.app.core.async.AsyncMethod;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.IOErrorEvent;
	import flash.events.SecurityErrorEvent;
	import flash.events.TimerEvent;
	import flash.net.URLLoader;
	import flash.net.URLRequest;
	import flash.utils.Timer;
	
	import mx.logging.ILogger;
	import mx.logging.Log;
	import mx.rpc.Fault;
	import mx.utils.UIDUtil;
	
	[Event(name="timeout", type="com.cisco.nbm.xmlrpc.v2.MediatorNodeCallEvent")]
	
	/**
	 * A call is a single, one-time operation that makes a request to a mediator.
	 * 
	 * It can only be used once. 
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 */
	public class MediatorNodeCall extends AsyncMethod //EventDispatcher
	{
		protected var _service:XMLRPCService;
		
		private var _name:String;
		
		private var _arguments:Array;
		
		private var _id:String;
				
		private var _loader:URLLoader;
		
		protected var _node:IMediatorNode;
		
		private var _timeout:int;
		
		private var timeoutTimer:Timer;
		
		private var logger:ILogger;

		public function MediatorNodeCall()//service:XMLRPCService, node:IMediatorNode, name:String, arguments:Array=null)
		{
			_id = UIDUtil.createUID();
			logger = Log.getLogger("cisco.nbm.net.v2.MediatorNodeCall." + _id);
			logger.debug("New mediator node call");
		}
		
		public function init(service:XMLRPCService, node:IMediatorNode, name:String, timeout:int, arguments:Array=null):void
		{
			_arguments = arguments;
			_name = name;
			_node = node;
			_service = service;
			_timeout = timeout;
		}
		
		public function get name():String
		{
			return _name;
		}
		
		public function get node():IMediatorNode
		{
			return _node;
		}
		
		public function execute(request:URLRequest):void
		{
			// start time
			logger.debug("Starting timeout with {0}", _timeout);
			
			if (_timeout < 1000) 
			{
				logger.warn("Timeout of {0} ms might be too fast", _timeout);
			}
			
			timeoutTimer = new Timer(_timeout, 1)
			timeoutTimer.addEventListener(TimerEvent.TIMER, handleTimerComplete);
			timeoutTimer.start();
			_loader.load(request);
		}
		
		private function handleTimerComplete(event:TimerEvent):void
		{
			logger.debug("timeout complete: finished? {0}", (finished ? "yes" : "no"));
			
			if (!finished)
			{
				setError("Timeout while waiting for the network call to complete");
				
				dispatchTimeoutError();
				
				dispatchError();
			}
		}
		
		private function dispatchTimeoutError():void
		{
			var event:MediatorNodeCallEvent = new MediatorNodeCallEvent(MediatorNodeCallEvent.TIMEOUT);
			dispatchEvent(event);
		}
		
		public function get id():String
		{
			return _id;
		}
		
		public function get result():Object
		{
			return _result;
		}
		
		internal function attachLoaderListeners(loader:URLLoader):void
		{
			_loader= loader;
	
			_loader.addEventListener(Event.COMPLETE, handleLoaderComplete);
			_loader.addEventListener(IOErrorEvent.IO_ERROR, handleLoaderError);
			_loader.addEventListener(SecurityErrorEvent.SECURITY_ERROR, handleLoaderError);
		}
		
		override protected function internalHandleComplete():void
		{
			_result = parseResult(_loader.data);
			
			if (_result is Fault)
			{
				throw new Error( (_result as Fault).message ); 
			}
		}
		
		protected function handleLoaderComplete(event:Event):void
		{
			if (timeoutTimer != null)
			{
				timeoutTimer.stop();
				timeoutTimer.removeEventListener(TimerEvent.TIMER, handleTimerComplete);
				timeoutTimer = null;
			}
			
			handleComplete();					
		}
		
		protected function parseResult(data:String):Object
		{
			var xml:XML = new XML(data);
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			return deserializer.deserialize(xml);
		}
			
		
		private function handleLoaderError(event:ErrorEvent):void
		{
			event.stopImmediatePropagation();
			setError(event.text);
			dispatchError();
		}
		
		override protected function cleanup():void
		{
			if (_loader != null)
			{
				_loader.removeEventListener(Event.COMPLETE, handleLoaderComplete);			
				_loader.removeEventListener(IOErrorEvent.IO_ERROR, handleLoaderError);
				_loader.removeEventListener(SecurityErrorEvent.SECURITY_ERROR, handleLoaderError);
			}
			
			if (timeoutTimer != null)
			{
				timeoutTimer.stop();
				timeoutTimer.removeEventListener(TimerEvent.TIMER, handleTimerComplete);
				timeoutTimer = null;
			}
		}
	}
}