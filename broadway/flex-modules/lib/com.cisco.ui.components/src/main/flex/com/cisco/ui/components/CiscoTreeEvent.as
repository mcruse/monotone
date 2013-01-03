package com.cisco.ui.components
{
	import flash.events.Event;

	public class CiscoTreeEvent extends Event
	{
		public static const CHANGING:String = "changing";
		
		public static const CHANGED:String = "changed";
		
		public var nextSelections:Array;
		
		public function CiscoTreeEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}