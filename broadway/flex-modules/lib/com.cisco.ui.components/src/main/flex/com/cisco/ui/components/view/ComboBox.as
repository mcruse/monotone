package com.cisco.ui.components.view
{
	import flash.events.KeyboardEvent;
	import flash.ui.Keyboard;
	
	import mx.collections.ArrayCollection;
	import mx.controls.ComboBox;
	import mx.controls.listClasses.ListBase;
	import mx.core.UIComponentGlobals;
	import mx.core.mx_internal;
	use namespace mx_internal;

	public class ComboBox extends mx.controls.ComboBox
	{
		public function ComboBox()
	    {
	        super();
	    }

		override protected function keyDownHandler(event:KeyboardEvent):void {
			if ( event.keyCode == Keyboard.SPACE ) {
				open();
			}
			super.keyDownHandler(event);
		}
		
		override public function set dataProvider(value:Object):void {
			super.dataProvider = value;
			var dropDownControl:ListBase = dropdown;
			if ( dropDownControl != null && dropDownControl.dataProvider != value ) {
				
				if (!dataProvider)
                	dropDownControl.dataProvider = new ArrayCollection();
                else
					dropDownControl.dataProvider = value;
					
				dropDownControl.rowCount = rowCount;
				dropDownControl.selectedIndex = selectedIndex;
				UIComponentGlobals.layoutManager.validateClient(dropDownControl, true);
				dropDownControl.setActualSize(dropdownWidth,dropDownControl.getExplicitOrMeasuredHeight());
				dropDownControl.invalidateDisplayList();
				invalidateSize();
				dropDownControl.invalidateList();
			}
		}
	}
}