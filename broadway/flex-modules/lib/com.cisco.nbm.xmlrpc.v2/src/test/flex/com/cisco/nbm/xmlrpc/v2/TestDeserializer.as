///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm.xmlrpc.v2
{
	import com.cisco.nbm.CiscoTestCase;
	
	import mx.formatters.DateFormatter;
	import mx.rpc.Fault;

	public class TestDeserializer extends CiscoTestCase
	{
		public function testInvalidCode():void
		{
			try
			{
				var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
				deserializer.deserialize(<invalid />);
				
				fail("Should have thrown an Error");
			} 
			catch (e:Error)
			{
				
			}
		}
		
		public function testDeserializeException():void
		{
			var errorResponse:XML =  <methodResponse>
					<fault>
						<value>
							<struct>
								<member>
									<name>faultCode</name>
									<value><int>1</int></value>
								</member>
								<member>
									<name>faultString</name>
									<value><string><![CDATA[exception]]></string>
									</value>
								</member>
							</struct>
						</value>
					</fault>
				</methodResponse>;
				
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(errorResponse);
			
			assertTrue("Result should be of type Fault", result is Fault);
			
			var faultResult:Fault = result as Fault;
			
			assertEquals("Fault code should be 1", faultResult.faultCode, 1);
			assertEquals("Fault string should be 'exception'",
				faultResult.faultString, "exception");
			
		}
		
		public function testDeserializeInteger():void
		{
			
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<int>1</int>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Result should be of type int", result is int);
			assertEquals("Result should be 1", result, 1);
		}
		
		public function testDeserializeDouble():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<int>2.0</int>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Result should be of type Number", result is Number);
			assertEquals("Result should be 2.0", result, 2.0);
		}
		
		public function testDeserializeDate():void
		{
			var today:Date = new Date();
			var dateFormatter:DateFormatter = new DateFormatter();
			dateFormatter.formatString = "YYYYMMDDTJJ:NN:SS";
			var dateString:String = dateFormatter.format(today);
				
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<dateTime.iso8601>{dateString}</dateTime.iso8601>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Result should be of type Date", result is Date);
			
			// Flex compares the dates based on milliseconds since epoch
			// since millis are not provided in xmlrpc date struct then we 
			// cut off to seconds and compare those
			assertEquals("Dates should match", Math.floor((result as Date).time/1000), Math.floor(today.time/1000));
		}
		
		public function testDeserializeString():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<string>baz</string>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type String", result is String);
			assertEquals("Response should equal 'baz'", result, "baz");
		}

		public function testDeserializeBooleanNumber():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<boolean>1</boolean>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type Boolean", result is Boolean);
			assertTrue("Response should true", result); 
		}
		
		public function testDeserializeBooleanWithWord():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<boolean>true</boolean>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type Boolean", result is Boolean);
			assertTrue("Response should true", result); 
		}
		

		public function testDeserializeArray():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<array>
								<data>
									<value><int>1</int></value>
									<value><string>baz</string></value>
								</data>
							</array>
						</value>
					</param>
				</params>
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type Array", result is Array);
			
			var correctValues:Array = [ 1, "baz" ];
			assertArraysEqual("Values should be equal", correctValues, result);
		}
		
		public function testDeserializeNestedArray():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<array>
								<data>
									<value><int>1</int></value>
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
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type Array", result is Array);
			
			var correctValues:Array = [ 1, [ "one", "two" ] ];
			
			assertArraysEqual("Values should be equal", correctValues, result);
		}
		
		public function testDeserializeStruct():void
		{
			var response:XML = <methodResponse>
				<params>
					<param>
						<value>
							<struct>
								<member>
									<name>name</name>
									<value><string>wallace</string></value>
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
			</methodResponse>
			
			var deserializer:XMLRPCDeserializer = new XMLRPCDeserializer();
			var result:* = deserializer.deserialize(response);
			
			assertTrue("Response should be of type Object", result is Object);
			
			assertEquals("Member name should be 'wallace'", 
				result.name, "wallace");
				
			var numbers:Array = [1, 2];
			assertArraysEqual("Numbers should be " + numbers,
				result.numbers, numbers);
		}
	}
}