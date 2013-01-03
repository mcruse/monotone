package com.cisco.ui
{
	import mx.formatters.Formatter;

	public class CiscoNumberFormatter extends Formatter
	{
		public var leadingZeros:int = 0;
		
		public function CiscoNumberFormatter()
		{
			super();
		}
		
		override public function format(value:Object):String
		{
			if (leadingZeros == 0)
			{
				return new String(value);
			}
			
			var str:String = "";
			var count:int = leadingZeros - 1;
			
			if (value > 9)
			{
				count -= 1;
			}
			
			for (var i:int = 0; i < count; i++)
			{
				str += "0";
			}
			
			return str + value.toString();
		}
		
	}
}