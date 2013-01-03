package com.cisco.ui.components.vo
{
	[Bindable]
	public class AdvancedSearchItem
	{
		public var displayName:String;
		public var label:String;
		public var enabled:Boolean;
		public var searchString:String;
		
		public function AdvancedSearchItem(label:String,displayName:String=null) {
			this.label = label;
			if ( displayName != null )
				this.displayName = displayName;
			else
				this.displayName = label;
		}
	}
}