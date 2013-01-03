package com.cisco.nbm.xmlrpc.v2
{
	import flash.events.Event;

	public class MediatorNodeCallEvent extends Event
	{
		public static const TIMEOUT:String = "timeout";
		
		public function MediatorNodeCallEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}