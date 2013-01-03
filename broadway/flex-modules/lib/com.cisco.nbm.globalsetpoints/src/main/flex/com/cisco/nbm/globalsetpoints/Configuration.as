package com.cisco.nbm.globalsetpoints
{
	dynamic public class Configuration 
	{
		
		private static var _instance:Configuration;
		
		public function Configuration()
		{
			if (_instance != null) {
				throw new Error("This is a singleton class. Use getInstance()");	
			}
		}
		
		public static function getInstance():Configuration {
			if (_instance != null) {
				return _instance;
			}
			
			_instance = new Configuration();
			
			return _instance;
		}

	}
}