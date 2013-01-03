package com.cisco.ui.components.vo
{
	public interface IXMLObject
	{
		function toXML():XML;
		function loadFromXML(xml:XML):void;
	}
}