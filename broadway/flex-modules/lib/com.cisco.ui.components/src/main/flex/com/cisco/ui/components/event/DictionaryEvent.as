package com.cisco.ui.components.event
{
	import flash.events.Event;

	public class DictionaryEvent extends Event
	{
		public static const ADD:String = "addDictionaryItemEvent";
		public static const REMOVE:String = "removeDictionaryItemEvent";
		
		public var key:String;
		public var value:Object;
		public var value2:Object;
		public function DictionaryEvent(type:String, key:String, value:Object=null,value2:Object=null, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			//TODO: implement function
			super(type, bubbles, cancelable);
			this.key = key;
			this.value = value;
			this.value2 = value2;
		}
		
	}
}