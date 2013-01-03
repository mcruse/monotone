package com.cisco.ui.components.event
{
	import flash.events.Event;

	public class UIDataEvent extends Event
	{
		public static const CLOSE:String = "windowClose";
		
		public var data:Object;
		public function UIDataEvent(type:String, data:Object=null,bubbles:Boolean=false, cancelable:Boolean=false)
		{
			//TODO: implement function
			super(type, bubbles, cancelable);
			this.data = data;
		}
		
		override public function clone():Event {
			return new UIDataEvent(type,data,bubbles,cancelable);
		}

	}
}