package com.cisco.nbm.globalsetpoints.entity
{
	import flash.events.Event;

	public class EntitySubscriberEvent extends Event
	{
		public static const READY:String = "ready";
		
		public function EntitySubscriberEvent(type:String)
		{
			super(type);
		}
		
		
		override public function clone():Event {
			var newEvent:EntitySubscriberEvent = new EntitySubscriberEvent(this.type);
			
			return newEvent;
		}
	}
}