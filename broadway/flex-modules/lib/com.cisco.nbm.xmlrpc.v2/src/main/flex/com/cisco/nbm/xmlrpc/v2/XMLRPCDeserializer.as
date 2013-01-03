///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import mx.rpc.Fault;
	import mx.utils.Base64Decoder;
	
	/**
	 * Deserializes an XML-RPC method call response.  
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 */
	public class XMLRPCDeserializer
	{
		/**
		 * Deserialize an XML-RPC response. 
		 * 
		 * If the response is a fault response then it will return a Fault object.
		 * Otherwise, a parsed response is returned.
		 * 
		 * @param xml The XML response
		 * @returns The parsed response
		 * @throws Error if it is not a valid XMLRPC response or fault
		 */
		public function deserialize(xml:XML):*
		{
			var result:XMLList = xml.params.param.value;
			
			if (result.toString() != "")
			{
				return decodeObject(result);
			}
			
			if (xml.fault.value != undefined)
			{
				var faultObject:* = decodeObject(xml.fault.value);
				var fault:Fault = new Fault(faultObject.faultCode, faultObject.faultString);
				
				return fault;
			} 
			else
			{
				throw new Error("Invalid XMLRPC format");
			}
			
			return decodeObject(xml);
		}
		
		public function decodeObject(xml:*):*
		{
			var nodeName:String;
			try {
				nodeName = xml.children().localName();
			} catch (ex:Error ) {
				
			}
			
			if (nodeName == "string")
			{
				return String(xml.string);
			}
			
			if (nodeName == "int")
			{
				return new int(xml.int);
			}
			if (nodeName == "i4")
			{
				return new int(xml.i4);
			}
			
			
			if (nodeName == "double")
			{
				return Number(xml.double);
			}
			
			if (nodeName == "boolean")
			{
				if (isNaN(xml.boolean))
				{
					if (String(xml.boolean).toLowerCase() == "true")
					{
						return true;
					}
					
					if (String(xml.boolean).toLowerCase() == "false")
					{
						return false;
					}
					
					return null;
				}
				else
				{
					return xml.boolean == 1;
				}
			}
			
			if (nodeName == "dateTime.iso8601")
			{
				var dateString:String = xml.children();
				var datePattern:RegExp = /^(-?\d{4})-?(\d{2})-?(\d{2})T(\d{2}):(\d{2}):(\d{2})/;
				var d:Array = dateString.match(datePattern);
				var date:Date = new Date(d[1], d[2] - 1, d[3], d[4], d[5], d[6]);
				
				return date;
			}
			
			if (nodeName == "base64")
			{
				var decoder:Base64Decoder = new Base64Decoder();
				decoder.decode(xml.base64);
				return decoder.flush();
			}
			
			if (nodeName == "array")
			{
				var array:Array = [];
				
				for each (var value:* in xml.array.data.value)
				{
					array.push(decodeObject(value));
				}
				
				return array;s
			}
			
			if (nodeName == "struct")
			{
				var object:Object = new Object();
				for each (var member:* in xml.struct.member)
				{
					object[member.name] = decodeObject(member.value);
				}
				
				return object;
			}
			
			if (nodeName == "nil")
			{
				return null;
			}
			
			return String(xml);
		}

	}
}