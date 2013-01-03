package com.cisco.ui.components.vo
{
	import flash.geom.Point;
	
	public interface IDraggable
	{
		function isDraggableArea(point:Point):Boolean;
	}
}