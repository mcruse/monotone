///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import flash.utils.ByteArray;
	
	import mx.formatters.DateFormatter;
	import mx.utils.Base64Encoder;
	
	/**
	 * TBD
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 * $Author: rocadena $ 
	 * $Date: 2010/01/09 00:46:05 $
	 * $Revision: 1.2 $
	 * $HeadURL$
	 * $Id: XMLRPCSerializer.as,v 1.2 2010/01/09 00:46:05 rocadena Exp $
	 */
	public class XMLRPCSerializer
	{
		private var _name:String;
		
		private var _params:Array;
		
		public function XMLRPCSerializer(name:String, params:Array=null)
		{
			_name = name;
			_params = params;
		}
		
		
		/**
		 */
		public function encodeObject(obj:*):XML
		{
			var paramNode:XML;
					
			if (obj is String) 
			{
				paramNode = <string>{obj}</string>;
			}
			else if (obj is Number) {
				
				if (Math.floor(obj) == obj) 
				{
					paramNode = <int>{obj}</int>;
				} 
				else 
				{
					paramNode = <double>{obj}</double>;
				}
			} 
			else if (obj is Boolean)
			{
				paramNode = <boolean>{obj ? 1 : 0}</boolean>
			} 
			else if (obj is Date) 
			{
				var dateFormatter:DateFormatter = new DateFormatter();
				dateFormatter.formatString = "YYYYMMDDTJJ:NN:SS";
				var dateString:String = dateFormatter.format(obj);
				
				paramNode = <dateTime.iso8601>{dateString}</dateTime.iso8601>;
			}
			else if (obj is Array)
			{
				
				var arrayDataNode:XML = <data />;
				
				for (var i:int = 0; i < obj.length; i++) 
				{
					arrayDataNode.appendChild(<value>{encodeObject(obj[i])}</value>);
				}
				
				paramNode = <array>{arrayDataNode}</array>;					
			}
			else if (obj is ByteArray)
			{
				var encoder:Base64Encoder = new Base64Encoder();
				encoder.encodeBytes(obj as ByteArray);
				paramNode = <base64>{encoder.flush()}</base64>;
			}
			else if (obj is IXMLRPCStruct)
			{
				paramNode = <struct />;
				var dataStruct:Object = (obj as IXMLRPCStruct).getPropertyData();
				
				for (var propName:* in dataStruct) 
				{
					paramNode.appendChild(<member><name>{propName}</name><value>{encodeObject(dataStruct[propName])}</value></member>);
				}
			}
			else if (obj is Object)
			{
				paramNode = <struct />
				
				for (var propName:* in obj) 
				{
					paramNode.appendChild(<member><name>{propName}</name><value>{encodeObject(obj[propName])}</value></member>);
				}
			}
			else if (obj == null)
			{
				paramNode = <nil/>;
			}
			else 
			{
				paramNode = <string>{obj as String}</string>;
			}
			
			return paramNode; 
		}
		
		public function serialize():XML
		{
			var xml:XML = <methodCall>
					<methodName>{_name}</methodName>
				</methodCall>
			
			var methodNode:XML = xml.methodName[0];
			
			
			if (_params != null && _params.length > 0) 
			{
				var paramsNode:XML = <params></params>
				
				for each (var param:* in _params)
				{
					paramsNode.appendChild(<param><value>{encodeObject(param)}</value></param>);
				}
				
				xml.insertChildAfter(methodNode, paramsNode);
			}
			
			return xml;
		}

	}
}