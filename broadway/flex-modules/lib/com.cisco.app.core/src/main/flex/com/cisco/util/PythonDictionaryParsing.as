///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.util
{
	import mx.utils.StringUtil;
	
	public class PythonDictionaryParsing
	{
		public function PythonDictionaryParsing()
		{
		}


		public function parse(source:String):Object
		{
			var value:Object;
			source = StringUtil.trim(source);
			
			// check the first character
			if (source[0] == "{")
			{
				value = parseDictionary(source);
			}
			else if (source[0] == "[")
			{
				value = parseArray(source);
			}
			else if (source[0] == "(")
			{
				value = parseTuple(source);
			}
			else if (source[0] == "'")
			{
				value = parseString(source);
			}
			
			return value;
		}
		
		private function parseDictionary(source:String):Object
		{
			return null;
		}
		
		private function parseArray(source:String):Array
		{
			return null;
		}
		
		private function parseTuple(source:String):Array
		{
			return null;
		}
		
		private function parseString(source:String):String
		{
			return null;
		}
	}
}