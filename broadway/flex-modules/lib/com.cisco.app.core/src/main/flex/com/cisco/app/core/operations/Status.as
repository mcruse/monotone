package com.cisco.app.core.operations
{
	public class Status
	{
		public static const OK:int = 1;
		
		public static const INFO:int = 2;
		
		public static const WARNING:int = 3
		
		public static const ERROR:int = 4;
		
		protected var _code:int;
		
		protected var _message:String;
		
		public function Status(code:int, message:String="")
		{
			_code = code;
			_message = message;
		}
		
		public function get code():int {
			return _code;
		}
		
		public function get message():String {
			return _message;
		}

	}
}