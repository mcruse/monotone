package com.cisco.nbm.scheduler.ui.components
{
	import com.cisco.nbm.scheduler.EventMetaData;
	
	import flash.events.Event;

	public class DailyEntryEditorEvent extends Event
	{
		public var time:int;
		
		public var rawValue:String;
		
		public static const TIME_UPDATED:String = "timeUpdated";
		
		public var eventMeta:EventMetaData;
		
		public function DailyEntryEditorEvent(time:int, eventMeta:EventMetaData, rawValue:String=null, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(TIME_UPDATED, bubbles, cancelable);
			this.eventMeta = eventMeta;
			this.time = time;
			this.rawValue = rawValue;
		}
		
	}
}