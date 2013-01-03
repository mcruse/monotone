package com.cisco.nbm.scheduler.ui.schedules
{
	import com.cisco.nbm.scheduler.DailyEntry;
	import com.cisco.nbm.scheduler.HierarchicalSchedule;
	
	import mx.collections.ArrayCollection;
	import mx.collections.ListCollectionView;
	import mx.events.CollectionEvent;
	import mx.events.CollectionEventKind;

	public class ScheduleGridCollection extends ListCollectionView
	{
		private var _schedule:HierarchicalSchedule;
		
		private var _rows:int = 0;
		
		public function ScheduleGridCollection()
		{
		}
		
		public function get schedule():HierarchicalSchedule
		{
			return _schedule;
		}
		
		public function getCellCoordinateForEntry(entry:DailyEntry):Object
		{
			if (_schedule == null)
			{
				return null;
			}
			
			var x:int = -1;
			var y:int = 0;
			
			var dailyEntries:ArrayCollection = _schedule.dailyEntries;
			
			for each (var entries:ArrayCollection in dailyEntries)
			{
				y = 0;
				
				for each (var otherEntry:DailyEntry in entries)
				{
					if (otherEntry === entry)
					{
						if (x == -1)  
						{
							x = 6; // Account for sunday being at the end in the display =(
						}
						
						return { rowIndex : y, columnIndex : x };
					}
					
					y++;
				}
				
				x++;
			}
			
			return null;
		}
		
		public function set schedule(value:HierarchicalSchedule):void
		{
			if (value !== _schedule)
			{
				detachListeners();
				_schedule = value;
				attachListeners();
				
				calculateRows();
			}
		}
		
		private function detachListeners():void
		{
			if (_schedule != null)
			{
				var dailyEntries:ArrayCollection = _schedule.dailyEntries;
				
				dailyEntries.removeEventListener(CollectionEvent.COLLECTION_CHANGE,
					handleEntriesChanged);
				
				
				for each (var entries:ArrayCollection in dailyEntries)
				{
					entries.removeEventListener(CollectionEvent.COLLECTION_CHANGE, handleEntriesChanged);
				}
			}
		}

		private function attachListeners():void
		{
			if (_schedule != null)
			{
				var dailyEntries:ArrayCollection = _schedule.dailyEntries;
				
				// attach to daily entries in case of change:
				dailyEntries.addEventListener(CollectionEvent.COLLECTION_CHANGE,
					handleEntriesChanged);
				
				for each (var entries:ArrayCollection in dailyEntries)
				{
					entries.addEventListener(CollectionEvent.COLLECTION_CHANGE, handleEntriesChanged);
				}
			}
		}
		
		private function handleEntriesChanged(event:CollectionEvent):void
		{
			trace("entries changed: " + event);
			calculateRows();
			dispatchEvent(new CollectionEvent(CollectionEvent.COLLECTION_CHANGE, false, false, CollectionEventKind.UPDATE));
		}
		
		private function calculateRows():void
		{
			var max:int = 0;
			
			if (_schedule != null)
			{
				var entries:ArrayCollection = _schedule.dailyEntries;
				
				for each (var entry:ArrayCollection in entries)
				{
					if (entry.length >= max)
					{
						max = entry.length;
					}
				}
			}
			
			_rows = max;
		}
		
		override public function getItemAt(index:int, prefetch:int=0):Object
		{
			// TODO Cache
			var row:Object = {};
			
			if (_schedule != null)
			{
				var entries:ArrayCollection = _schedule.dailyEntries;
				
				for each (var day:String in HierarchicalSchedule.DAY_INDEXES)
				{
					var cell:Object = null;
					var dayEntries:ArrayCollection = _schedule.getEntriesForDay(day);
					
					if (index < dayEntries.length)
					{
						cell = dayEntries[index];
					}
					
					row[day] = cell;
				}
			}

			return row;
		}
		
		override public function get length():int
		{
			return _rows;
		}
	}
}