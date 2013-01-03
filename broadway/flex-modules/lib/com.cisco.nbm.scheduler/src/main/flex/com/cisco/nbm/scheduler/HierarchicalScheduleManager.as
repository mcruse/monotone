package com.cisco.nbm.scheduler
{
	import com.cisco.app.core.async.AsyncMethod;
	import com.cisco.cisco_internal;
	import com.cisco.nbm.scheduler.jobs.SaveScheduleJob;
	import com.cisco.nbm.xmlrpc.v2.IMediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;
	import flash.events.EventDispatcher;
	import flash.events.TimerEvent;
	import flash.utils.Timer;
	
	import mx.collections.ArrayCollection;
	import mx.events.PropertyChangeEvent;
	import mx.logging.ILogger;
	import mx.logging.Log;
	
	
	[Event(name="complete", type="flash.events.Event")]
	[Event(name="error", type="flash.events.ErrorEvent")]
	public class HierarchicalScheduleManager extends EventDispatcher
	{
		use namespace cisco_internal;
		
		cisco_internal var _node:IMediatorNode;
		
		private var cachedSchedules:Object = {};
		
		public var rootSchedules:ArrayCollection = new ArrayCollection();
		
		private var logger:ILogger;
		
		private var isLoadedTimer:Timer;
		
		public function HierarchicalScheduleManager()
		{
			logger = Log.getLogger("cisco.schedules.HierarchicalScheduleManager");
		}
		
		
		
		public function get children():ArrayCollection
		{
			return rootSchedules;
		}
		
		public function init(node:IMediatorNode):void
		{
			_node = node;
			
			checkIsLoaded();
			
			// commented this out so we can call is_loaded  
			//getSchedules();
		}
		
		private function checkIsLoaded():void {
			logger.debug("checkIsLoaded");
			
			_node.execute("is_loaded", [])
				.addCallback(handleIsLoadedResult, handleIsLoadedError);
		}
		
		private function handleIsLoadedResult(call:MediatorNodeCall, result:Object):void {
			logger.debug("handleIsLoaded: {0}", result);
			
			if (result == true) {
				dispatchEvent(new Event(Event.COMPLETE));
				return;
			} 
			
			isLoadedTimer = new Timer(5000, 1);
			isLoadedTimer.addEventListener(TimerEvent.TIMER, handleIsLoadedTimer);
			logger.debug("will check again in {0} seconds", (isLoadedTimer.delay/1000.0));
			isLoadedTimer.start();
		}
		
		private function handleIsLoadedTimer(event:TimerEvent):void {
			logger.debug("is loaded timer, checking again");
			isLoadedTimer = null;
			checkIsLoaded();
		}
		
		private function handleIsLoadedError(call:MediatorNodeCall, error:Object):void {
			logger.error("Unable to find out if mediator node is ready: " + error);
			dispatchEvent(new ErrorEvent(ErrorEvent.ERROR, false, false, "Error calling is_loaded: " + error));
		}
		
		public function save(schedule:HierarchicalSchedule):SaveScheduleJob
		{			
			var job:SaveScheduleJob = new SaveScheduleJob(schedule, this);
			return job;
		}
		
		
		
		public function move(origin:Array /* of HierarchicalSchedule */, destination:Object):MediatorNodeCall
		{
			var paths:Array /* of String */ = [];
			
			for each (var originSchedule:HierarchicalSchedule in origin) {
				paths.push(originSchedule._node.path);
				// block any calls
				originSchedule.blockCalls = true;
			}  
			
			var call:MediatorNodeCall = _node.execute("move_schedule", 
				[paths, destination._node.path] );
			
			call.token =  { original : origin, destination : destination };
			call.addCallback(handleMoveComplete, handleMoveError);
			
			return call;
		}
		
		public function rename(schedule:HierarchicalSchedule, newName:String):MediatorNodeCall
		{
			if (schedule.readOnly)
			{
				throw new Error("Schedule is read-only");
			}
			
			var newPath:String = schedule._node.path;
			var basePath:String = newPath.substring(0, newPath.lastIndexOf("/"));
			newPath = basePath + "/" + newName;
			
			var call:MediatorNodeCall = 
				_node.execute("move_schedule", [schedule._node.path, newPath]);
			
			call.token = { schedule : schedule , newPath : newPath };
			call.addCallback(handleRenameComplete, handleRenameError);
			
			return call;
		}
		
		private function handleRenameComplete(method:AsyncMethod, result:Object):void
		{
			var token:Object = method.token;
			var schedule:HierarchicalSchedule = token.schedule as HierarchicalSchedule;
			var newPath:String = token.newPath;
			
			// can we just change the path?
			schedule._node.setPath(newPath);
			schedule.name = schedule._node.name;
		}
		
		private function handleRenameError(method:AsyncMethod, result:Object):void
		{
			throw new Error("Unable to rename schedule: " + result);
		}
		
		/**
		 * Called after moving the schedules.  It fixes their paths
		 * to have the parent path.
		 * 
		 * All child schedules inside this schedule must be fixed too!
		 */
		private function handleMoveComplete(method:AsyncMethod, result:Object):void
		{
			// The path needs to be adjusted when moving ...		
			var token:Object = method.token;	
			var destination:Object = token.destination;
			var originals:Array /* of HierarchicalSchedule */ = token.original;
			
			for each (var original:HierarchicalSchedule in originals) {
				var originalPath:String = original._node.path;
				var baseName:String = originalPath.substr(originalPath.lastIndexOf("/")+1);
				var destinationParentPath:String = destination._node.path;
				
				var newPath:String = destinationParentPath + "/" + baseName;
				
				original._node.setPath(newPath);
				
				// handle case where the original schedule was in the root.
				if (original.parent == null)
				{
					var idx:int = rootSchedules.getItemIndex(original);
					// NOTE Temporary, is giving us -1
					if (idx != -1) {
						this.rootSchedules.removeItemAt(idx);
					}
				}
				original.overrideStatus = true;
					
				destination.addChildSchedule(original);
				original.initialize(true);
				
			
				original.blockCalls = false;
			}
		}
		
		private function addChildSchedule(schedule:HierarchicalSchedule):void
		{
			if (rootSchedules.getItemIndex(schedule) == -1)
			{
				var oldParent:HierarchicalSchedule = schedule.parent;
				
				if (oldParent != null)
				{
					oldParent.removeChildSchedule(schedule);
				}
				
				schedule.parent = null;
				
				schedule.fixDescendantsPath(this, schedule);
				
				rootSchedules.addItem(schedule);
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "children", null, rootSchedules)); 
			}
		
		}
		
		private function handleMoveError(method:AsyncMethod, error:Object):void
		{
			throw new Error("Unable to move schedule: " + error);			
		}
		
		public function removeSchedule(schedules:Array /* of HierarchicalSchedule */):AsyncMethod//schedule:HierarchicalSchedule):AsyncMethod
		{
			var paths:Array /* of String */ = [];
			
			for each (var schedule:HierarchicalSchedule in schedules) {
				paths.push(schedule._node.path);
			}
			
			var call:MediatorNodeCall = _node.execute("remove_schedule", [ paths ]);
			call.token = { schedules: schedules };
			call.addCallback(handleRemoveScheduleResult, handleRemoveScheduleError);
			
			return call;
		}
				
		private function handleRemoveScheduleResult(method:MediatorNodeCall, result:Object):void
		{
			logger.debug("removed schedules: " + result);
			var token:Object = method.token;
			
			var parentSchedule:HierarchicalSchedule = token.parent;
			var deletedSchedules:Array /* of HierarchicalSchedule */ = token.schedules;
			
			for each (var deletedSchedule:HierarchicalSchedule in deletedSchedules) {
				if (deletedSchedule.parent != null) {
					// Remove from parent
					
					var parentSchedule:HierarchicalSchedule = deletedSchedule.parent;
					parentSchedule.removeChildSchedule(deletedSchedule);
					
				} else {
					// Remove from root
					var idx:int = rootSchedules.getItemIndex(deletedSchedule);
					if (idx != -1) {
						rootSchedules.removeItemAt(idx);
					}
				}
			}
		}
		
		/**
		 * Retrieves the list of schedule names and only adds those that are new
		 */
		private function updateRootSchedules():void {
			var call:MediatorNodeCall = _node.execute("children_schedule_names", null);
			call.addCallback(handleUpdateRootNamesResult, handleUpdateRootNamesError);
		}
		
		private function handleUpdateRootNamesResult(method:MediatorNodeCall, result:Object):void {
			var names:Array = result as Array;
			
			var found:Boolean = false;
			for each (var name:String in names) {
				found = false;
				for each (var sched:HierarchicalSchedule in this.rootSchedules) {
					if (sched.name == name) {
						found = true;
						break;
					} 
				}
				
				if (found) {
					continue;
				}
				var schedule:HierarchicalSchedule = new HierarchicalSchedule();
				schedule.initFromNode(null,  _node.getService().getNode(_node.path + "/" + name) as MediatorNode);
				
				rootSchedules.addItem(schedule);
			}
		}
		
		private function handleUpdateRootNamesError(method:MediatorNodeCall, error:Object):void {
			throw new Error("Unable to update root schedules after modification");
		}
		
		private function handleRemoveScheduleError(method:MediatorNodeCall, error:Object):void
		{
			throw new Error("Unable to remove schedule: "+ error);
		}
		
		
		// This gets the root of the schedules
		public function getSchedules():void
		{
			rootSchedules.removeAll();
			
			//var call:MediatorNodeCall = _node.execute("children_schedules", null);
			var call:MediatorNodeCall = _node.execute("children_schedule_names", null);
			//var call:MediatorNodeCall = _node.execute("children_nodes", null);
			call.addCallback(handleChildrenNamesResult, handleChildrenNamesError);
		}

		public function createSchedule(root:HierarchicalSchedule, newName:String):MediatorNodeCall
		{
			var uri:String = _node.path;
			
			if (root != null)
			{
				uri = root._node.path
			}
			
			var call:MediatorNodeCall = _node.execute("create_schedule", [newName, uri]);
			call.token = { root : root, name : newName };
			call.addCallback(handleCreateScheduleResult, handleCreateScheduleError);
			
			return call;
		}
		
		private function handleCreateScheduleResult(call:AsyncMethod, result:Object):void
		{
			var root:HierarchicalSchedule = call.token.root as HierarchicalSchedule;
			var name:String = call.token.name;
			
			if (root != null)
			{
				//root.forceGetChildren();
				root.internalLoadChildSchedule(name);
			}
			else
			{
				// This will remove all the schedules and reload them, 
				// we need to add it and then initialize it
				var newSchedule:HierarchicalSchedule = new HierarchicalSchedule();
				newSchedule.initFromNode(null, _node.getService().getNode(_node.path+"/" + name) as MediatorNode);
				rootSchedules.addItem(newSchedule);
				//getSchedules();
			}
		}
		
		private function handleCreateScheduleError(call:AsyncMethod, error:Object):void
		{
			throw new Error("Unable to create schedule: "+ error);
		}
				
		private function handleChildrenNamesResult(method:AsyncMethod, result:Object):void
		{
			rootSchedules.removeAll();
			
			for each (var nodeName:String in result)
			{
				var schedule:HierarchicalSchedule = new HierarchicalSchedule();
				schedule.initFromNode(null,  _node.getService().getNode(_node.path + "/" + nodeName) as MediatorNode);
				
				rootSchedules.addItem(schedule);
			}
			
			trace("got all the root schedules");
		}
		
		private function handleChildrenNamesError(method:AsyncMethod, error:Object):void
		{
			throw new Error("Unable to get children names");
		}
		
		
	}
}