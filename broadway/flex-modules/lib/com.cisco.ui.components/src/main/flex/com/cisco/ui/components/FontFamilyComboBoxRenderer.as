package com.cisco.ui.components
{
	import mx.controls.Label;
	import mx.events.FlexEvent;

	public class FontFamilyComboBoxRenderer extends Label
	{
		public function FontFamilyComboBoxRenderer()
		{
			super();
		}
		
		override public function set data(value:Object):void {
			super.data = value;
			if (value != null) {
				setStyle("fontFamily", value.fontName);
				text = value.fontName;
			}
			dispatchEvent(new FlexEvent(FlexEvent.DATA_CHANGE));
		}
		
	}
}