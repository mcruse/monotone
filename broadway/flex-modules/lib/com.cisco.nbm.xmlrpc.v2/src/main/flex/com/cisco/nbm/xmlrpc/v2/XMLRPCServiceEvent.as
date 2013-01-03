package com.cisco.nbm.xmlrpc.v2
{
	import flash.events.Event;

	public class XMLRPCServiceEvent extends Event
	{
		public static const CALL_COMPLETE:String = "callComplete";
		
		public function XMLRPCServiceEvent(type:String, bubbles:Boolean=false, cancelable:Boolean=false)
		{
			super(type, bubbles, cancelable);
		}
		
	}
}