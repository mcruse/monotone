package com.cisco.nbm.scheduler.components
{
	import flash.events.Event;

	public class WeekdayTimeValueEditorEvent extends Event
	{
		//public static const DOUBLE_CLICK:String = "wtveDoubleClick";
		
		public static const ITEM_EDIT_BEGINNING:String = "itemEditBeginning";
		
		public static const ITEM_EDIT_BEGIN:String = "itemEditBegin";
		
		public static const ITEM_EDIT_END:String = "itemEditEnd";
		
		public function WeekdayTimeValueEditorEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}