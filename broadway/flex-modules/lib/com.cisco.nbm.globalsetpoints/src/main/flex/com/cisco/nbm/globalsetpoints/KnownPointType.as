package com.cisco.nbm.globalsetpoints
{
	public class KnownPointType
	{
		private static var _list:Array;
		
		public function KnownPointType()
		{
			_list = new Array();
		}
		
		public static function get list():Array{
			return _list;
		}
		
		public static function set list(__list:Array):void{
			_list = __list;
		}
	}
}