package com.cisco.ui.components
{
	import flash.events.Event;
	import flash.events.TimerEvent;
	import flash.media.Video;
	import flash.utils.Timer;

	public class DelayedTimer extends Timer
	{
		private var _item:Object;
		private var _caller:Object;
		private var _func:Function;
		
		public function DelayedTimer()
		{
			super(1000, 1)
		}
		
		
		
		public function get caller():Object
		{
			return _caller;
		}
		
		public function set caller(value:Object):void
		{
			_caller = value;
		}
		
		public function get item():Object
		{
			return _item;
		}
		
		public function set item(value:Object):void
		{
			_item = value;
		}
		
		public function get func():Function
		{
			return _func;
		}
		
		public function set func(value:Function):void
		{
			_func = value;
		}
		
		public function startDelayedTimer(func:Function, event:Event=null, caller:Object=null, delay:Number=1000, repeat:int=1, item:Object=null):void
		{
			if (func == null)
			{
				return;
			}
			
			this.item = item;
			this.func = func;
			
			if (this.caller != null)
			{
				this.caller = caller;
				
				if (event != null)
				{
					if (this.caller != event.target)
					{
						this.caller = event.target;
					}
				}
			}
			
			if (running == true)
			{
				cancelDelayedTimer();
			}
			
			this.delay = delay;
			this.repeatCount = repeat;
			
			addEventListener(TimerEvent.TIMER, func, false, 0, true);
			
			start();
		}
		
		public function cancelDelayedTimer():void
		{
			if (hasEventListener(TimerEvent.TIMER))
			{
				removeEventListener(TimerEvent.TIMER, func);
			}
			
			if (running == true)
			{
				_func = null;
				_caller = null;
				_item = null;
				stop();
				reset();
			}
		}
		
	}
}