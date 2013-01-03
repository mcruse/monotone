package com.cisco.nbm.scheduler.components
{
	import flash.events.Event;
	
	import mx.controls.Label;
	import mx.core.UIComponent;

	public class DailyHourRuler extends UIComponent
	{
		private static const MINUTES_IN_DAY:Number = 24.0 * 60.0;
		
		private var pixelToMinuteRatio:Number = 1;
		
		private var middle:Number = 0;		
		
		private var minTimeIntervals:Array = [ 15.0, 30.0, 60.0, 60.0*12.0 ];
		
		private var minSelectedTimeInterval:int = 0;
		
		private static const DESIRED_HEIGHT:int = 10;
		
		private static const FILLED_RECT_HEIGHT:int = 4;
		
		private static const LABEL_Y_OFFSET:int = 8;
		
		private var labels:Array = [];
		
		public function DailyHourRuler()
		{
			super();
			
			addEventListener(Event.RESIZE, handleResize);
		}
	
		override protected function measure():void
		{
			super.measure();
			
			measuredHeight = Label(labels[0]).getExplicitOrMeasuredHeight() + LABEL_Y_OFFSET;
		}
		
		override protected function createChildren():void
		{
			super.createChildren();
			
			if (labels.length == 0)
			{
				var tempLabel:Label = new Label();
				tempLabel.text = "Midnight";
				labels.push(tempLabel);
				
				tempLabel = new Label();
				tempLabel.text = "6 AM";
				labels.push(tempLabel);
				
				tempLabel = new Label();
				tempLabel.text = "Noon";
				labels.push(tempLabel);
				
				tempLabel = new Label();
				tempLabel.text = "6 PM";
				labels.push(tempLabel);
				
				tempLabel = new Label();
				tempLabel.text = "Midnight";
				labels.push(tempLabel);
			}
			
			for each (var elem:Label in labels)
			{
				addChild(elem);
			}
		}
		
		override protected function updateDisplayList(
			unscaledWidth:Number, unscaledHeight:Number):void
		{
			super.updateDisplayList(unscaledWidth, unscaledHeight);
		
			graphics.clear();
			
			var quarterInterval:Number = unscaledWidth / 4;
			var currX:int = 0;
			
			var rectHeight:int = FILLED_RECT_HEIGHT; 
			
			// draw the rectangle for 12-6am, then 6-12pm
			graphics.beginFill(0, 0.3);
			graphics.drawRect(0, 0, quarterInterval, rectHeight);
			graphics.endFill();
		
			currX = quarterInterval;
			graphics.beginFill(0xFFCC33, 1);
			graphics.drawRect(quarterInterval, 0, quarterInterval*2, rectHeight);
			graphics.endFill();
			
			graphics.beginFill(0, 0.3);
			graphics.drawRect(quarterInterval*3, 0, quarterInterval, rectHeight);
			graphics.endFill();
		
			// Draw the 4 line intervals
			graphics.lineStyle(1, 0, 1, true);
			
			for (var i:int = 0; i < 5; i++)
			{
				currX = i * quarterInterval;
				graphics.moveTo(currX, 0);
				graphics.lineTo(currX, LABEL_Y_OFFSET - 2);
			}	
			var currY:int = LABEL_Y_OFFSET;
			var labelWidth:int = 0;
			var label:Label = labels[0];
			
			// setup midnight morning
			label.move(0, currY);
			label.setActualSize(label.getExplicitOrMeasuredWidth(), 
				label.getExplicitOrMeasuredHeight());
			// setup 6am in the middle
			label = labels[1];
			label.setActualSize(label.getExplicitOrMeasuredWidth(), 
				label.getExplicitOrMeasuredHeight());
			labelWidth = label.getExplicitOrMeasuredWidth()
			label.move(quarterInterval - (labelWidth/2), currY);
			
			// Mid day
			label = labels[2];
			label.setActualSize(label.getExplicitOrMeasuredWidth(), 
				label.getExplicitOrMeasuredHeight());
			labelWidth = label.getExplicitOrMeasuredWidth();
			label.move((quarterInterval * 2) - (labelWidth /2), currY);
			
			// 6 pm
			label = labels[3];
			label.setActualSize(label.getExplicitOrMeasuredWidth(), 
				label.getExplicitOrMeasuredHeight());
			labelWidth = label.getExplicitOrMeasuredWidth();
			label.move((quarterInterval * 3) - (labelWidth /2), currY);
			
			
			label = labels[4];
			label.setActualSize(label.getExplicitOrMeasuredWidth(), 
				label.getExplicitOrMeasuredHeight());
			labelWidth = label.getExplicitOrMeasuredWidth();
			label.move(unscaledWidth - labelWidth, currY);
			
						
		}
		
		private function handleResize(event:Event):void
		{
			pixelToMinuteRatio = width / MINUTES_IN_DAY;
			
		}
	}
}