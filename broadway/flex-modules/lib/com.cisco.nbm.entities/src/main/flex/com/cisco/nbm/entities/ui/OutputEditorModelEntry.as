package com.cisco.nbm.entities.ui
{
	public class OutputEditorModelEntry
	{
		[Bindable]
		public var level:int;
		
		[Bindable]
		public var value:Object;
		
		[Bindable]
		public var active:Boolean = false;
		
		public function OutputEditorModelEntry(level:int, value:Object=null)
		{
			this.level = level;
			this.value = value;
		}


		public function toString():String
		{
			return "OutputEditorModelEntry(level="+level+", value="+value+")";
		}
	}
}