package com.cisco.nbm.scheduler.ui
{
	import com.cisco.nbm.scheduler.ScheduleDocument;
	
	import flash.events.Event;

	public class ScheduleDocumentEvent extends Event
	{
		/**
		 * Events of this type indicate that the document's schedule object has changed
		 * to a different schedule
		 */
		public static const SCHEDULE_CHANGE:String = "scheduleChange";
		
		/**
		 * Events of this type indicate that the schedule has been mdoified and
		 * may be dirty or clean.
		 */
		public static const SCHEDULE_MODIFIED:String = "scheduleModified";
		
		public var document:ScheduleDocument;
		
		public function ScheduleDocumentEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}