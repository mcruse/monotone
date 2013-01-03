package com.cisco.ui.components.view
{
	import com.cisco.ui.components.util.Util;
	
	import flash.events.Event;
	import flash.events.FocusEvent;
	
	import mx.controls.TextInput;

	public class FilterTextInput extends TextInput
	{
		public function FilterTextInput()
		{
			//TODO: implement function
			super();
			addEventListener(FocusEvent.FOCUS_IN,onFocusIn);
			addEventListener(FocusEvent.FOCUS_OUT,onFocusOut);
			//this.text = "Find";
			onFocusOut();
		}

		public function onFocusIn(event:FocusEvent=null):void {
			if (this.styleName == "GreyLabel" && this.text == "Find"  ) {
				this.text = '';
				this.styleName = "BlackLabel";
				dispatchEvent(new Event("styleChange"));
			}
		}


		public function onFocusOut(event:FocusEvent=null):void {
			if ( this.text == '' ){
				this.text = "Find";
				this.styleName = "GreyLabel";
				dispatchEvent(new Event("styleChange"));
			}
		}

		public function clear():void {
			this.text = '';
		}

		
		[Bindable("styleChange")]
		public function get inSearchMode():Boolean {
			return this.styleName == "BlackLabel";
		}

		public function search(searchString:String):Boolean {
			return inSearchMode?((Util.search(searchString, this.text) == -1)?false:true):true;
		}

	}
}