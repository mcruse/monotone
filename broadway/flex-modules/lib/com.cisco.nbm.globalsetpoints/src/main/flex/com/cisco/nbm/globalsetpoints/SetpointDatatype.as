package com.cisco.nbm.globalsetpoints
{
	public class SetpointDatatype
	{
		public static const TEXT:String       = "Text";
		public static const NUMERIC:String    = "Numeric";
		public static const ENUMERATED:String = "Enumerated";
		
		private static const typeArray:Array = [TEXT, NUMERIC, ENUMERATED];
		
		public function SetpointDatatype()
		{
		}
		
		public static function get LIST():Array{
			return typeArray;
		}
		
		public static function indexOf(value:String):Number{
			for(var i:int = 0; i< typeArray.length; i++){
				if(typeArray[i] == value){
					return i;
				}
			}
			return -1;
		}
	}
}