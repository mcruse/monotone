///////////////////////////////////////////////////////////////////////////////
// Cisco - Network Building Management
// Copyright 2009-2010 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.app.core.async
{
	/**
	 * An empty call that can be extended.
	 */
	public class EmptyCall extends AsyncMethod
	{
		public function EmptyCall(result:Object=null, error:Object=null)
		{
			super();
			this._error = error;
			this._result = result;
			
			if (this._error != null)
			{
				this.wasError = true;
			}
			handleComplete();
		}
	}
}