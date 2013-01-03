package com.cisco.nbm.scheduler.ui.components.eventmetaeditor
{
	import mx.utils.StringUtil;
	import mx.validators.ValidationResult;
	import mx.validators.Validator;

	public class EventMetaValueValidator extends Validator
	{
		private var _results:Array;
		
		public static const ERROR_EMPTY_VALUE:String = "EmptyValue";
		
		public var _emptyValueErrorMessage:String = "Value cannot be empty";
		
		
		
		public function EventMetaValueValidator()
		{
		}
	
		public function set emptyValueErrorMessage(value:String):void
		{
			_emptyValueErrorMessage = value;
		}
		
		public function get emptyValueErrorMessage():String
		{
			return _emptyValueErrorMessage;
		}
	
		override protected function doValidation(value:Object):Array
		{
			var stringValue:String = StringUtil.trim(String(value));
			
			_results = [];
			
			_results = super.doValidation(value);
			
			if (_results.length > 0)
			{
				return _results;
			}
			
			if (stringValue.length == 0)
			{
				_results.push(new ValidationResult(true, null, ERROR_EMPTY_VALUE, _emptyValueErrorMessage));
			}
			
			return _results;
		}	
	}
}