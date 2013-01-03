package com.cisco.nbm.scheduler.ui.components.customvaluemap
{
	import com.cisco.nbm.scheduler.ScheduleProperty;
	
	public class CustomValueMapEntry
	{
		[Bindable]
		public var name:String;
		
		[Bindable]
		public var realValue:Object;
		
		public var metaUUID:String;
		
		[Bindable]
		public var customValue:Object;
		
		[Bindable]
		public var level:int;
		
		public var property:ScheduleProperty;
		
		public function CustomValueMapEntry()
		{
		}

		public function destroy():void
		{
			property = null;
		}
	}
}