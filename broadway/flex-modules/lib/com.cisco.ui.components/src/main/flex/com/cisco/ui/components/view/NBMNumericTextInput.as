package com.cisco.ui.components.view
{
	import mx.controls.TextInput;

	public class NBMNumericTextInput extends TextInput
	{
		public function NBMNumericTextInput() {
			super();
			restrict = "0-9\\-\\.\\,";
		}
	}
}