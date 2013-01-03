package com.cisco.nbm.xmlrpc.v2
{
	import com.cisco.nbm.CiscoTestCase;

	public class TestRPCURIParser extends CiscoTestCase
	{
		
		public function testParserStraightPath():void
		{
			var uri:String = "http://mpxadmin:baz@192.168.20.20/XMLRPCv2/RNA/services/time";
			
			var parser:URIParser = new URIParser();
			parser.parse(uri);
			
			assertTrue("Username should be 'mpxadmin'", "mpxadmin", parser.username);
		}
	}
}