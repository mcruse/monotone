package com.cisco.ui.components.vo
{
	public interface IValueObject
	{
		function clone():IValueObject;
		function copyFrom(value:IValueObject):void;
	}
}