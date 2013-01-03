package com.cisco.nbm.globalsetpoints.event
{
	import flash.events.Event;
	
	public class ReleaseOverrideEvent extends Event
	{
		public static const RELEASE:String  = "release";
		public static const COMPLETE:String = "complete";
		
		public var setpointId:String;
		public var priority:String;
		
		public function ReleaseOverrideEvent(type:String)
		{
			super(type);
		}
		
		override public function clone():Event {
			var newEvent:ReleaseOverrideEvent = new ReleaseOverrideEvent(this.type);
			
			return newEvent;
		}

	}
}