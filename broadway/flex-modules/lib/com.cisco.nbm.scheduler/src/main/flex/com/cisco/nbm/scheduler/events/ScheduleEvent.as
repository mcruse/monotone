package com.cisco.nbm.scheduler.events
{
	import flash.events.Event;

	public class ScheduleEvent extends Event
	{
		public static const SUMMARY_COMPLETE:String = "summaryComplete";
		
		public static const METADATA_UPDATED:String = "metaDataUpdated";
		
		public static const DAILENTRY_UPDATED:String = "dailyEntryUpdated";
		
		public static const PROPERTY_UPDATED:String = "propertyUpdated";
		
		public static const EXCEPTIONS_UPDATED:String = "exceptionsUpdated";
		
		public var item:Object;
		
		public function ScheduleEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}