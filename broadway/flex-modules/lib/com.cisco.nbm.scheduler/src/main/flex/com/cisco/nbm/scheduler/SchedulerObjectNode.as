package com.cisco.nbm.scheduler
{
	import com.cisco.nbm.xmlrpc.v2.MediatorNode;
	import com.cisco.nbm.xmlrpc.v2.MediatorNodeCall;
	
	import flash.events.ErrorEvent;
	import flash.events.Event;

	public class SchedulerObjectNode extends MediatorNode
	{
		public var summary:Object;
		
		public function SchedulerObjectNode()
		{
			super();
		}
	
		public function get_summary():void
		{
			var call:MediatorNodeCall = createMediatorNodeCall("get_summary");
			call.addEventListener(Event.COMPLETE, handleGetSummaryComplete);
			call.addEventListener(ErrorEvent.ERROR, handleGetSummaryError);
			
			// =(
		}	
		
		private function handleGetSummaryComplete(event:Event):void
		{
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
		
			cleanupCall(call, [ Event.COMPLETE, handleGetSummaryComplete ],
					[ErrorEvent.ERROR, handleGetSummaryError]);
					
			parseGetSummaryResult(call.result);
			
		}
		
		private function handleGetSummaryError(event:ErrorEvent):void
		{
			var call:MediatorNodeCall = event.target as MediatorNodeCall;
		
			cleanupCall(call, [ Event.COMPLETE, handleGetSummaryComplete ],
					[ErrorEvent.ERROR, handleGetSummaryError]);
		
		}
		
		private function parseGetSummaryResult(result:Object):void
		{
			
		}
	}
}