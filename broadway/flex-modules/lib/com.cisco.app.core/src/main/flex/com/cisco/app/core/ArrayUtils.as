package com.cisco.app.core
{
	public class ArrayUtils
	{
		/**
		 * Performs a comparison of array <code>a</code> and <code>b</code>.
		 * 
		 * The array compares the objects using strict equality ===
		 */
		public static function equal(a:Array, b:Array):Boolean {
			if (a.length != b.length) {
				return false;
			}
			
			for (var i:int = 0; i < a.length; i++) {
				if (a[i] !== b[i]) {
					return false;
				}
			}
			
			return true;
		}
		
		/**
		 * Replace all the elements in <code>a</code> with all the elements
		 * in <code>b</code>.
		 */
		public static function replace(a:Array, b:Array):void {
			b.splice(0, b.length);
			
			for each (var obj:Object in a) {
				b.push(obj);
			}
		}
		
		/**
		 * Creates a new array with the contents of <code>src</code>.
		 * 
		 * It doesn't actually duplicate or clone each of the objects in 
		 * <code>src</code>, it merely creates a new array with those objects.
		 */
		public static function copy(src:Array):Array {
			var newArray:Array = [];
			
			for each (var obj:Object in src) {
				newArray.push(obj);
			}
			
			return newArray;
		}
	}
}