package com.cisco.nbm.browserbridge
{
	import flash.events.Event;

	public class BrowserBridgeEvent extends Event
	{
		
		public static const READY:String = "ready";
		
		public static const ERROR:String = "error";
		
		public static const PRE_INIT:String = "preinit";
		
		public var message:String;
		
		public function BrowserBridgeEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}