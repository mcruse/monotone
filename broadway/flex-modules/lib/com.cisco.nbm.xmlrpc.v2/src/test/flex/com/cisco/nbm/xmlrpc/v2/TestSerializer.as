///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import flexunit.framework.TestCase;
	
	import mx.formatters.DateFormatter;
	
	/**
	 * Tests for XMLRPCSerializer
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 * 
	 * $Author: rocadena $ 
	 * $Date: 2009/11/09 21:39:37 $
	 * $Revision: 1.1 $
	 * $HeadURL$
	 * $Id: TestSerializer.as,v 1.1 2009/11/09 21:39:37 rocadena Exp $
	 */ 
	public class TestSerializer extends TestCase
	{
		
		public function testSerializeBasic():void
		{
			var today:Date = new Date();
			var dateFormatter:DateFormatter = new DateFormatter();
			dateFormatter.formatString = "YYYYMMDDTJJ:NN:SS";
			var dateString:String = dateFormatter.format(today);
			
			var subSubArray:Array = [ "one", "two" ];
			var subArray:Array = [ 1, 2, 3, subSubArray ];
			
			
			var correctXML:XML = <methodCall><methodName>foo</methodName>
				<params>
					<param>
						<value>
							<boolean>1</boolean>
						</value>
					</param>
					<param>
						<value>
							<string>one</string>
						</value>
					</param>
					<param>
						<value>
							<double>2.3</double>
						</value>
					</param>
					<param>
						<value>
							<int>2</int>
						</value>
					</param>
					<param>
						<value>
							<dateTime.iso8601>{dateString}</dateTime.iso8601>
						</value>
					</param>
					<param>
						<value>
							<array>
								<data>
									<value><int>1</int></value>
									<value><int>2</int></value>
									<value><int>3</int></value>
									<value>
										<array>
											<data>
												<value><string>one</string></value>
												<value><string>two</string></value>
											</data>
										</array>
									</value>
								</data>
							</array>
						</value>
					</param>
					
					
					
				</params>
			</methodCall>;

			var params:Array = [ true, "one", 2.3, 2, today, subArray ];
			var methodCall:XMLRPCSerializer = new XMLRPCSerializer("foo", params);
			var resultXML:XML = methodCall.serialize();
			
			assertEquals("XMLs should match", correctXML, resultXML);
		}
		
		/**
		 * We split this test off here because when encoding parameters from 
		 * an object we can't be guaranteed that the parameter order will 
		 * be the same across runs, so we compare by actually finding the paths
		 * in the xml
		 */
		public function testSerializeStruct():void
		{
			var someObject:Object = { name : 'wallace', age : 32, numbers : [1, 2] };
			var correctXML:XML = <methodCall><methodName>foo</methodName>
				<params>
					<param>
						<value>
							<struct>
								<member>
									<name>name</name>
									<value>
										<string>wallace</string>
									</value>
								</member>
								<member>
									<name>age</name>
									<value><int>32</int></value>
								</member>
								<member>
									<name>numbers</name>
									<value>
										<array>
											<data>
												<value><int>1</int></value>
												<value><int>2</int></value>
											</data>
										</array>
									</value>
								</member>	
							</struct>
						</value>
					</param>
				</params>
			</methodCall>;
			
			var params:Array = [ someObject ];
			var methodCall:XMLRPCSerializer = new XMLRPCSerializer("foo", params);
			var resultXML:XML = methodCall.serialize();
			
			assertNotUndefined("Should have a member 'name' node",  
				resultXML.params.param.value.struct.member.(name == "name") )
				
			assertEquals("Value of name param should be 'name'",
				resultXML.params.param.value.struct.member.(name == "name").name.toString(),
				"name"); 
					
		}
	}
}