package com.cisco.nbm.scheduler
{
	import flash.events.EventDispatcher;
	
	import mx.events.PropertyChangeEvent;
	
	public class DailyEntry extends EventDispatcher
	{
		private var _time:int;
		
		private var _value:Object;
		
		private var _name:String;
		
		private var _eventName:String;
		
		private var _eventMeta:EventMetaData;
		
		
		public static function fromValues(nameVal:String, timeVal:String, valueVal:String):DailyEntry
		{
			var entry:DailyEntry = new DailyEntry();
			entry._name = nameVal;
			entry._time = DailyEntry.parseTimeString(timeVal);
			entry._value = valueVal;
			
			return entry;
		}
		
		public function updateFromMeta():void
		{
			value = _eventMeta.value;
		}
		
		public function toMPXArray():Array
		{
			return [ name, toMPXString(), value ];
		}
		
		public static function timeStringInHoursMinutes(entry:DailyEntry):String
		{
			var am_pm:String = "AM";
			var hours:Object = entry.hours;
			
			if (hours >= 12)
			{
				am_pm = "PM";
				hours = Number(hours) - 12;
			}
			
			if (hours == 0)
			{
				hours = 12;
			}
			
			hours = hours < 10 ? "0" + hours : "" + hours;
			
			var minutes:Object = entry.minutes;
			
			minutes = minutes < 10 ? "0" + minutes : "" + minutes; 
			
			return hours + ":" + minutes + " " + am_pm;
		}
		
		/**
		 * Parses a string in the following format: HH:MM:SS 
		 * 
		 * If the time does not follow that format then it is set to 00:00:00
		 * 
		 */
		private static function parseTimeString(timeString:String):int
		{
			var vals:Array = timeString.split(":");
			
			if (vals.length < 3)
			{
				return 0;
			}
			
			for each (var i:String in vals)
			{
				if (isNaN(Number(i)))
				{
					return 0;
				}
			}
			
			if (int(vals[0]) >= 24 || int(vals[1]) >= 60 || int(vals[2]) >= 60)
			{
				return 0;
			}
			
			return (int(vals[0]) * 60 * 60) + (int(vals[1]) * 60) + int(vals[2]);
		}
		
		/**
		 * The number of seconds since midnight of any day.
		 */
		public function get time():int
		{
			return _time;
		}
		 
		
		 
		public function set eventMeta(value:EventMetaData):void
		{
			if (_eventMeta != value)
			{
				var oldValue:EventMetaData = _eventMeta;
				
				_eventMeta = value;
				if (_eventMeta != null)
				{
					//trace("updating meta value: " + 
					this.value = _eventMeta.value;
				}
				else
				{
					this.value = "";
				}
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "eventMeta", oldValue, _eventMeta));
			}
		}
		
		public function get eventMeta():EventMetaData
		{
			return _eventMeta;
		}
		 
		public function set time(value:int):void
		{
			if (value !== _time)
			{
				var oldValue:int = _time;
				_time = value;
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "time", oldValue, _time));
			}
		}
		 
		/**
		 * The hour for this day, starting at 0
		 */
		public function get hours():int
		{
			return _time / 3600;
		}
		
		public function set hours(value:int):void
		{
			var minutes_seconds:int = (minutes * 60) + seconds;
			time = (value * 3600) + minutes_seconds;
		}
		
		/**
		 * The number of minutes since the hour
		 */
		public function get minutes():int
		{
			return (_time / 60) % 60;
		}
		
		public function set minutes(value:int):void
		{
			var hours_seconds:int = (hours * 3600) + seconds;
			time = hours_seconds + (value * 60);
		}
		
		/**
		 * The number of seconds since the minute
		 */
		public function get seconds():int
		{
			return _time % 60;
		}
		
		public function set seconds(value:int):void
		{
			var hours_minutes_seconds:int = (hours * 3600) + (minutes * 60) + value;
			time = hours_minutes_seconds;
		}
		
		public function get value():Object
		{
			return _value;
		}
		
		public function set value(v:Object):void
		{
		//	if (v != _value)
			{
				var oldValue:Object = _value;
				
				_value = v;
				
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "value", oldValue, _value));
				dispatchEvent(PropertyChangeEvent.createUpdateEvent(this, "time", oldValue, _value)); // ???
			}
		}
		
		public function get name():String
		{
			return _name;
		}
		
		public function set name(value:String):void
		{
			_name = value;
		}
		
		/*
		public function get color():int
		{
			return _color;
		}
		
		public function set color(value:int):void
		{
			trace("set: "  + value);
			_color = value;
		}
		*/
		
		public function toMPXString():String
		{
			var str:String = "";
			
			if (hours < 10)
			{
				str =  "0" + hours;
			}
			else
			{
				str = new String(hours);
			}
			
			str += ":";
			
			if (minutes < 10)
			{
				str += "0" + minutes;
			}
			else
			{
				str += new String(minutes);
			}
			
			str += ":";
			
			if (seconds < 10)
			{
				str += "0" + seconds;
			}
			else
			{
				str += new String(seconds);
			}
			
			return str;
		}
		
		override public function toString():String
		{
			return "[name='" + _name + "', time=" + hours + ":" + minutes + ":" + seconds + ", value='" + _value + "']";
		}
	}
}