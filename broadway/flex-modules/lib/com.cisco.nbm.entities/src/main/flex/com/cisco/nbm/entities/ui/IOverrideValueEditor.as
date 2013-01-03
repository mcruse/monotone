package com.cisco.nbm.entities.ui
{
	import com.cisco.nbm.entities.EntityProperty;
	
	import mx.core.IFlexDisplayObject;

	public interface IOverrideValueEditor extends IFlexDisplayObject
	{
		function get value():Object;
		
		function set value(v:Object):void;
				
		function get initialized():Boolean;
	}
}