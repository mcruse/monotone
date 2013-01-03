package com.cisco.ui.components.util
{
	import mx.utils.StringUtil;
	
	public class Util
	{
		public static function search(source:String, expression:String):int {
			return ( source.toLowerCase().indexOf(StringUtil.trim(expression).toLowerCase()));
		}
	}
}