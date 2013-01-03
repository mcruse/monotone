///////////////////////////////////////////////////////////////////////////////
// Cisco
// Copyright 2009 Cisco 
// All Rights Reserved
///////////////////////////////////////////////////////////////////////////////
package com.cisco.nbm
{	
	import flexunit.framework.AssertionFailedError;
	import flexunit.framework.TestCase;


	/**
	 * Base test case that adds some additional assert methods.
	 * 
	 * @author Robert Cadena <rocadena@cisco.com>
	 * $Author: rocadena $ 
	 * $Date: 2009/11/09 21:39:37 $
	 * $Revision: 1.1 $
	 * $HeadURL$
	 * $Id: CiscoTestCase.as,v 1.1 2009/11/09 21:39:37 rocadena Exp $
	 */
	public class CiscoTestCase extends TestCase
	{
		/**
		 * Assert the equality of two arrays by comparing the elements of each
		 * array.  It recursively checks elements of type array.
		 * 
		 * @param msg A human readable message
		 * @param a The reference array
		 * @param b The array to compare
		 * @throws AssertionFailedError if the elements of the array do not match
		 */
		public function assertArraysEqual(msg:String, a:Array, b:Array):void
		{
			if (a.length != b.length) 
			{
				throw new AssertionFailedError(msg + " - was: " + a + ", expected: " + b);
			}
			
			for (var i:int = 0; i < a.length; i++) {
				var elemA:Object = a[i];
				var elemB:Object = b[i];
				
				if (elemA is Array && elemB is Array) {
					try 
					{
						assertArraysEqual(msg, elemA as Array, elemB as Array);
					}
					catch (e:AssertionFailedError) 
					{
						throw new AssertionFailedError(msg + " - error in subarray");
					}
					
					continue;
				}
				
				if (elemA != elemB)
				{
					throw new AssertionFailedError(msg + " - was: " + a+ ", expected: " + b);
				}
			}
		}
	}
}