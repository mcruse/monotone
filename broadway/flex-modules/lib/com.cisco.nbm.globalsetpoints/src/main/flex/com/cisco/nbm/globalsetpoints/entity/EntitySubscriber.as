package com.cisco.nbm.globalsetpoints.entity
{
	
	import com.cisco.nbm.globalsetpoints.Configuration;
	
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.utils.Timer;
	[Event(name="onPollResult", type="flash.events.Event")]
	[Event(name="ready", type="com.cisco.nbm.globalsetpoints.entity.EntitySubscriberEvent")]
	
	public class EntitySubscriber extends EventDispatcher
	{
		import com.cisco.nbm.xmlrpc.v2.MediatorNode;
		import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
		import mx.collections.ArrayCollection;
		
		private static const DEFAULT_POLL_FREQUENCY:int = 1000 * 10; // 10 seconds
		
		private var subscriptionNode:MediatorNode;
		private var subscriptionId:String;
		private var subscriptionConfig:Object;
		private var subscriptionResult:ArrayCollection;
		private var entities:ArrayCollection;
		
		private var _running:Boolean = false;
		
		private var _polling:Boolean = false;
		
		private var _timer:Timer;
		
		
		private var keyToIndex:Object = {};
		
		
		/**
		 * Poll frequency in milliseconds.
		 * 
		 * Changing this value does not change a currently running timer.  The user
		 * should stop and then start the subscriber after changing the value.
		 */
		public var frequency:int = DEFAULT_POLL_FREQUENCY;
		
		public var poollAllCount:int = 0;
		
		/* private static const subscriptionConfig:Object = 
			{
				'ahu-1-rat' : '/aliases/Building A/Roof/ahu-1/AI/rat'
				// another_node_key : node_path,
				// one_more_node_key : and_its_path					
			}; */
			
		public function EntitySubscriber(_subscriptionNode:MediatorNode)
		{
			subscriptionNode = _subscriptionNode;
			
			var config:Configuration = Configuration.getInstance();
			
			if (config.hasOwnProperty("pollFrequency")) {
				
				frequency = config.pollFrequency;
				trace("custom pol lfrequency: " + frequency);
			}
		}
		
		public function start():void {
			if (_running) {
				trace("already running with subscription id: " + subscriptionId);
				return;
			}
			
			_running = true;
			_timer = new Timer(frequency);
			_timer.addEventListener(TimerEvent.TIMER, handleTimer);
			_timer.start();
			
			pollAll();
		}
		
		public function stop():void {
			trace("stopping");
			if (!_running) {
				return;
			}
			
			_running = false;
			
			if (subscriptionId != null) {
				subscriptionNode.execute("destroy", [ subscriptionId ]);
			}
			subscriptionId = null;
			
			if (_timer != null) {
				if (_timer.running) {
					_timer.stop();
				}
				
				
				_timer.removeEventListener(TimerEvent.TIMER, handleTimer);					
			}
			
			_timer = null;
			_polling = false;
		}
		
		private function handleTimer(event:TimerEvent):void {
			trace("timer:" + _running);
			
			if(poollAllCount > 1){
				return; // Only poll twice
			}
			
			if (!_running || _polling) {
				return;
			}
		
			pollChanged();
					
		}
		
		// Update manually
		public function refresh():void {
			if(_polling || !_running){
				return;
			}
			pollChanged();
		}
		
		public function get isRunning():Boolean {
		 	return _running;
		}
		
		public function create(_entities:ArrayCollection):void {
			
			keyToIndex = {};
			
			subscriptionResult = new ArrayCollection();
			
			if (subscriptionId != null) {
				trace("subscription already exists");
				return;
			}
			
			entities = _entities;
			// Construct key value for subscription
			subscriptionConfig = new Object();
			
			var len:int = entities.length;

			for(var k:int=0; k<len; k++){
				var keystr:String = entities.getItemAt(k).entity_path
				+"|"+entities.getItemAt(k).type
				+"|"+entities.getItemAt(k).property; 
				
				var pathstr:String = entities.getItemAt(k).entity_path
				+"/"+entities.getItemAt(k).type
				+"/"+entities.getItemAt(k).property; 
				
				subscriptionConfig[keystr] = pathstr;
			}
			// Node call
			subscriptionNode.execute("create_polled", [subscriptionConfig])
				.addCallback(handleCreatePolledResult, handleCreatePolledError);
		}
		
		public function getValueFor(entityObj:Object):String{
			if(subscriptionResult == null) return '..';
			
			for(var i:int = 0; i< subscriptionResult.length; i++){
				if(subscriptionResult.getItemAt(i).entity_path == entityObj.entity_path && 
				   subscriptionResult.getItemAt(i).type  == entityObj.type && 
				   subscriptionResult.getItemAt(i).property == entityObj.property){
					return subscriptionResult.getItemAt(i).value;
				}
			}
			
			return '..';
		}
		
		private function handleCreatePolledResult(method:MediatorNodeCall, result:Object):void {
			trace("handleCreatePolled: " + result);
			
			subscriptionId = result as String;
			//pollAll();
			dispatchEvent(new EntitySubscriberEvent(EntitySubscriberEvent.READY));
		}
		
		private function handleCreatePolledError(method:MediatorNodeCall, error:Object):void {
			trace("ERROR IN CREATE POLLED: " + error);
		}
		
		public function pollAll():void {
			_polling = true;
			var cb:MediatorNodeCall = subscriptionNode.execute("poll_all", [ subscriptionId ] );
			
			if (cb.token == null) { // Workaround for token being prepulated in certain calls
				cb.token = { };
			}
			
			
			cb.token.subscriptionId = subscriptionId;
			cb.addCallback(handlePollResult, handlePollError);
			poollAllCount = 0;
		}
		
		private function pollChanged():void {
			_polling = true;
			var cb:MediatorNodeCall = subscriptionNode.execute("poll_changed", [ subscriptionId ] );
			
			if (cb.token == null) { // Workaround for token being prepulated in certain calls
				cb.token = { };
			}
			
			cb.token.subscriptionId = subscriptionId ;	
			
			cb.addCallback(handlePollResult, handlePollError);			
		}
		
		private function handlePollResult(method:MediatorNodeCall, result:Object):void {
			trace("handlePolLResult: " + result);
			/* for (var key:String in result) {
				trace("'" + key + "': '" + result[key].value + "'");
			} */
			_polling = false;
		
			if (method.token.subscriptionId != subscriptionId) {
				trace("subscription ids do not match");
				return;
			}
			
			// Parse into array collection
			
			//subscriptionResult = new ArrayCollection();
			
			
			for (var key:String in result) {
				var keyarr:Array = key.split("|");
				var obj:Object = new Object();
				obj.entity_path = keyarr[0];
				obj.type        = keyarr[1];
				obj.property    = keyarr[2];
				if (result[key] != null) {
					
					trace("'" + key + "' = '" + result[key].value + "'");
					obj.value       = result[key].value;
				}
			
				if (keyToIndex[key] == null) {
					subscriptionResult.addItem(obj);
					var index:int = subscriptionResult.length-1;
					keyToIndex[key] = index;
					trace("adding new item to index: " + index + " for key " + key);
				} else {
					trace("updating item at : " + keyToIndex[key] + " for key: " + key);
					subscriptionResult.getItemAt(keyToIndex[key]).value = obj.value;
				}
			
				
			}
			
			// Dispatch complete event
			var onChangeEvent:Event = new Event( "onPollResult" );
			dispatchEvent( onChangeEvent );
			
			// Retry
			poollAllCount++;
		}
		
		private function handlePollError(method:MediatorNodeCall, error:Object):void {
			trace("HANDLE POLL ERROR: " + error);
			
			_polling = false;
		}
	}
}