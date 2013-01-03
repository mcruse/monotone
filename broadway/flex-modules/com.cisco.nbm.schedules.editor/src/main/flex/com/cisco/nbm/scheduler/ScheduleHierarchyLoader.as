package com.cisco.nbm.scheduler
{
	import com.cisco.cisco_internal;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	import com.cisco.nbm.xmlrpc.v2.XMLRPCService;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.utils.Timer;
	import flash.utils.getTimer;
	
	import mx.collections.ArrayCollection;
	import mx.core.Application;
	
	use namespace cisco_internal;
	/**
	 * Dispatches complete when all the schedule names have been loaded
	 * and parsed into a hierarchy.
	 */
	[Event(name="complete", type="flash.events.Event")]
	
	/**
	 * Dispatched if there's an error while trying to retrieve the schedules
	 */
	[Event(name="error", type="flash.events.ErrorEvent")]
	public class ScheduleHierarchyLoader extends EventDispatcher
	{
		public static const DEFAULT_DELAY:Number = 100;
		
		/**
		 * @private 
		 * 
		 * The query identifier used to continue querying the manager
		 */
		private var qid:String = null;
		
		private var scheduleNames:Array = [];
		
		[Bindable]
		public var schedules:ArrayCollection = new ArrayCollection();
		
		/**
		 * @private
		 * The node that points to the Query Manager on the mediator
		 * 
		 */
		private var queryManagerNode:MediatorNode;
		
		private var manager:HierarchicalScheduleManager;
		
		/**
		 * @private
		 * 
		 * The timer that is used (in place of call later) to retrieve the next batch
		 * from an incomplete query result.  
		 */
		private var timer:Timer;
		
		public function ScheduleHierarchyLoader(queryManagerNode:MediatorNode,
			manager:HierarchicalScheduleManager)
		{
			this.queryManagerNode = queryManagerNode;
			this.manager = manager;
			
			service = queryManagerNode.getService();
		}
		
		/**
		 * Currently will load ALL the schedules and return them
		 */
		public function load():void {
			fetch();
		}
		
		private function fetch():void {
			var query:Object = { 'query' : 
				{'schedules' : true,
				 'context' : '/services/Schedule Manager'} };
			
			if (qid != null) {
				query = { 'qid' : qid };
			}
			
			var array:ArrayCollection = new ArrayCollection();
			
			var call:MediatorNodeCall = queryManagerNode.execute("fetch", [query]);
			call.addCallback(handleSchedulesResult, handleSchedulesError);
		}
		
		private function handleSchedulesResult(call:MediatorNodeCall, result:Object):void {
			trace("schedules result: " + result);
			
			trace("complete: " + result.complete);
			trace("qid: " + result.qid);
			trace("length: " + result.items.length);
			
			if (result.qid != null) {
				trace("setting query id: " + qid);
				qid = result.qid;
			}
			
			// result { complete : false, count XXXX, length = XXX, qid = XXX, expider : false, items : array }
			for each (var name:String in result.items) {
				//array.addItem(name);
				scheduleNames.push(name);
			}
			
			
			if (result.complete) {
				scheduleResultComplete();
				return;
			}
			
			// call later
			timer = new Timer(DEFAULT_DELAY, 1);
			timer.addEventListener(TimerEvent.TIMER, handleTimer);
			timer.start();
		}
		
		var cache:Object = {};
		var scheduleManagerPrefix:String = "/services/Schedule Manager";
		var startIndex:uint = scheduleManagerPrefix.length;  // length of the prefix we're trying to remove
		var service:XMLRPCService;
			
		private function scheduleResultComplete():void {
			// sort them first (we'll do better sorting so that it's no lexicographic)
			scheduleNames.sort();
			
			var maxTime:int = 100; // 400 ms time while parsing
			
			var startTime:int = getTimer();
			
			// now we create ALL the schedule objects
			
			//var cache:Object = {};
			var i:int = 0;
			for each (var path:String in scheduleNames) {
				i++;
				
				var escPath:String = unescape(path);
				
				// The results will include /services/Schedule Manager, so we skip it
				if (escPath == scheduleManagerPrefix) {
					continue;
				}
				
				// +1 for initial forward slash
				var schedulePath:String = escPath.substr(startIndex+1);
				//chedules.addItem(schedulePath);
				
				// We need to find the parent of the new schedule.
				// We split the path into tokens
				// Since a schedule may be deeply nested, we check each token,
				// reconstructing the path.  Example.
				// /A1/B1/C1
				// Check for A1, if not, create
				// Check for B1, if not, create
				// B1 is parent of C1, C1 will get created with new schedule, 
				// /A1 and /A1/B1 will be cached
				var tokens:Array = schedulePath.split("/");
				var tempPath:String = "";
				var parentSchedule:HierarchicalSchedule = null;
				for each (var token:String in tokens) {
					tempPath += token;
					//trace("checking cache for " + tempPath);
					var sched:HierarchicalSchedule = cache[tempPath];
					
					if (sched == null) {
						if (parentSchedule != null) {
							trace("Creating " + tempPath + " with parent: " + parentSchedule._node.path);
						} else {
							trace("Creating " + tempPath + " on ROOT");
						}
						//trace(tempPath + "doesn't exist, creating");
						sched = new HierarchicalSchedule();
						sched.initFromNode(parentSchedule, service.getNode(scheduleManagerPrefix + "/" + tempPath) as MediatorNode);
						
						if (parentSchedule == null) {
							manager.rootSchedules.addItem(sched);
						} else {
							parentSchedule._children.addItem(sched);
						}
						
						sched._loadedChildren = true; // turn off the flag
						cache[tempPath] = sched;
					}
					
					parentSchedule = sched;
					
					tempPath += "/";
				}
				
				var now:int = getTimer();
				
				if (now - startTime > maxTime) {
					trace("breaking parsing to be nice ...");
					
					scheduleNames.splice(0, i);
					
					Application.application.callLater(scheduleResultComplete);
					return;
				}

			}
			
			dispatchComplete();
		}
		
		private var callBackTimer:Timer;
		
		private function handleSchedulesError(call:MediatorNodeCall, error:Object):void {
			trace("error getting schedules: " + error);
			
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, "Error fetching schedules: " + error));
		}
		
		private function dispatchComplete():void {
			dispatchEvent(new Event(Event.COMPLETE));
		}
		
		private function handleTimer(event:TimerEvent):void {
			trace("fetching again");
			timer.removeEventListener(TimerEvent.TIMER, handleTimer);
			timer = null;
			
			fetch();
		}

	}
}