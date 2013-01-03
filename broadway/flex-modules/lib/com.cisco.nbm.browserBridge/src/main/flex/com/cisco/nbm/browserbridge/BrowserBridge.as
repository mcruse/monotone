package com.cisco.nbm.browserbridge
{
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.external.ExternalInterface;
	import flash.utils.Timer;
	import flash.utils.getTimer;
	
	import mx.core.Application;
	import mx.logging.ILogger;
	import mx.logging.Log;

	[Event(name="ready", type="com.cisco.nbm.browserbridge.BrowserBridgeEvent")]
	[Event(name="preinit", type="com.cisco.nbm.browserbridge.BrowserBridgeEvent")]
	[Event(name="error", type="com.cisco.nbm.browserbridge.BrowserBridgeEvent")]
	public class BrowserBridge extends EventDispatcher
	{
		private var initialized:Boolean = false;
		
		private var _isReady:Boolean = false;
		
		private var _isAvailable:Boolean = false;
		
		private var logger:ILogger = Log.getLogger("cisco.nbm.browserBridge");
		
		public var args:Object = {};
		
		public var topicListeners:Object = {};
		
		public var topicHandlers:Object = {};
		
		public static const DEFAULT_TIMEOUT:int = 2000;
		
		private var _timeout:int = DEFAULT_TIMEOUT;
		
		private var _timeStart:int = -1;
		
		public function BrowserBridge()
		{
			super();
		}
		
		public function set timeout(value:int):void
		{
			_timeout = value;
		}
		
		public function get isReady():Boolean
		{
			return _isReady;
		}
		
		public function init():void
		{
			if (initialized)
			{
				return;
			}
			
			_timeStart = getTimer();
			
			initialized = true;
			
			parseArgs();
			
			if (ExternalInterface.available)
			{
				try
				{
					addCallback("sendToWidget", receivedFromContainer);
					addCallback("topicNotification", handleTopicNotification);
					
					if (checkJavaScriptReady())
					{
						javaScriptIsReady();
					}
					else
					{
						beginCheckJSTimer();
					}
				}
				catch (e:SecurityError)
				{
					logger.error("SecurityError initializing: {0}", e);
					dispatchErrorEvent("Security error: " + e.message);
					return;
				}
				catch (e:Error)
				{
					logger.error("Generic error initializing: {0}", e);
					dispatchErrorEvent("General error: " + e.message);
				}
			}
			else
			{
				dispatchErrorEvent("No external interface");
			}
		}
		
		private function parseArgs():void
		{
			var params:Object = Application.application.parameters;
			
			for (var key:String in params)
			{
				args[key] = params[key];
			}
			
		}
		
		public function addCallback(methodName:String, handler:Function):void
		{
			ExternalInterface.addCallback(methodName, handler);
			ExternalInterface.call("cisco.NBMBridge._addExternalInterfaceCallback", 
						ExternalInterface.objectID, methodName);
		}
		
		private function dispatchErrorEvent(message:String=null):void
		{
			var failEvent:BrowserBridgeEvent = new BrowserBridgeEvent(BrowserBridgeEvent.ERROR);
			failEvent.message = message
				
			dispatchEvent(failEvent);	
		}
		
		private function javaScriptIsReady():void
		{
			_isReady = true;
			dispatchEvent(new BrowserBridgeEvent(BrowserBridgeEvent.PRE_INIT));
			
			ExternalInterface.call("cisco.NBMBridge.loaded", ExternalInterface.objectID);
			
			logger.debug("sending to external bridge that widget is loaded.  ID: '" + ExternalInterface.objectID + "'");
			
			dispatchEvent(new BrowserBridgeEvent(BrowserBridgeEvent.READY));
		}
		
		private function checkJavaScriptReady():Boolean
		{
			//var val:Boolean  = ExternalInterface.call("cisco.NBMBridge.isWidgetReady", ExternalInterface.objectID);
			var val:Boolean  = ExternalInterface.call("cisco.NBMBridge.isReady");
			logger.debug("ready? " + val);
			return val;
		}
		
		private function beginCheckJSTimer():void
		{
			var checkJSTimer:Timer = new Timer(1000, 0);
			checkJSTimer.addEventListener(TimerEvent.TIMER, handleCheckJSTimer);
			checkJSTimer.start();
		}
			
		private function handleCheckJSTimer(event:TimerEvent):void
		{
			var isReady:Boolean = checkJavaScriptReady();
			
			if (isReady)
			{
				Timer(event.target).stop();
				javaScriptIsReady();
				return;
			}
			
			var now:int = getTimer();
			
			if (now - _timeStart > _timeout)
			{
				Timer(event.target).stop();
				dispatchErrorEvent("Timeout after " + _timeout + "ms while waiting for the shell to respond");
			}
		}
		
		/**
		 * Execute a call into the browser
		 */
		public function executeCall(methodName:String,  ... args):Object
		{
			return ExternalInterface.call("cisco.NBMBridge._call", ExternalInterface.objectID, methodName, args); 
		}
		
		public function subscribe(topic:String, handler:Function):void
		{
			var handlers:Array = topicListeners[topic];
			
			if (handlers == null)
			{
				handlers = [];
				topicListeners[topic] = handlers;
			}
			
			if (topicHandlers[topic] == undefined)
			{
				logger.debug("No handler defined for topic {0}, registering: ", topic);
				var handler:Function = function ( event : Object ):void { handleTopicReceived(topic, event) };
				topicHandlers[topic] = handler;
			}
			
			var idx:int = handlers.indexOf(handler);
			if (idx == -1)
			{
				handlers.push(handler);
				executeCall("subscribe", topic, "handleTopicReceived"); 
			}
		}
		
		public function unsubscribe(topic:String, handler:Function):void
		{
			var handlers:Array = topicListeners[topic];
			
			if (handlers != null)
			{
				var idx:int = handlers.indexOf(handler);
				
				if (idx != -1)
				{
					handlers.splice(idx, 1);
				}
				
				if (handlers.length == 0)
				{
					if (topicHandlers[topic] != undefined)
					{
						delete topicHandlers[topic];
					}
					
					delete topicListeners[topic];
				}
			}
		}
		
		public function publish(topic:String, event:Object):void
		{
			ExternalInterface.call("dojo.publish", topic, [event]);
		}
		
		private function handleTopicReceived(topic:String, event:Object):void
		{
			logger.debug("handle topic received: " + topic + ": " + event);
		}
			
		private function receivedFromContainer(value:String):void
		{
			logger.debug("container said: " + value);
		}
		
		private function handleTopicNotification(result:Object):void
		{
			logger.debug("handle topic notification: " + result);
		}
	}
}