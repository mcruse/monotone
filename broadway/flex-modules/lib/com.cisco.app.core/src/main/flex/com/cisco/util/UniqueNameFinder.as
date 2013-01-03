///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.util
{
	import mx.utils.StringUtil;
	
	public class UniqueNameFinder
	{
		
		public function UniqueNameFinder()
		{
		}
		
		private function escapeRegEx(value:String):String
		{
			return value.replace(new RegExp("([{}\(\)\^$&.\*\?\/\+\|\[\\\\]|\]|\-)", "g"), "\\$1");
		}
		
		public function find(prefix:String, names:Array /* of String */):String
		{
			var max:int = 0;//names.length;
			var re:RegExp = new RegExp( "^" + escapeRegEx(prefix) + "\ (\\d*)" );
			
			for each (var name:String in names)
			{
				var currNum:int = 0;
				// Skip if the name does not contain the prefix
				if (name.indexOf(prefix) != 0)
				{
					continue;
				}
				
				if (name == prefix)
				{
					max++;
					
					continue;
				}
				
				var matches:Object = re.exec(name);
				
				if (matches != null)
				{
					currNum = new Number(matches[1]) + 1;
				}
				
				if (currNum > max)
				{
					max = currNum;
				}
			}
			
			var result:String = prefix;
			
			if (max != 0)
			{
				result += " " + (max);
			}
			
			return result;
		}

	}
}