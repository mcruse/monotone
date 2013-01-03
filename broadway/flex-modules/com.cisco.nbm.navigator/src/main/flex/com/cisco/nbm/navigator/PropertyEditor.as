package com.cisco.nbm.navigator
{
	import com.cisco.nbm.entities.EntityProperty;
	
	import flash.display.DisplayObject;
	
	public class PropertyEditor
	{
		public var property:EntityProperty;
			
		private var _control:GenericPropertyEditorControl;
			
		private var _value:Object;
			
		public function PropertyEditor(property:EntityProperty)
		{
			this.property = property;
			
		}
		
		public function setValue(value:Object):void
		{
			_value = value;
			
			updateControlValue();
		}
		
		private function updateControlValue():void
		{
			if (_control != null && _value != null)
			{
				_control.setValue(_value);
			}
		} 
		
		public function createControl():void
		{
			// TODO Move to factory
			switch (property.type)
			{
				//case "Analog Input":
				default:
					_control = new GenericPropertyEditorControl();	
			}
			
			_control.property = property;
			updateControlValue();			
		}

		public function get control():DisplayObject
		{
			return _control;
		}
		
		public function destroy():void
		{
			_control = null;
			property = null;
		}
	}
}