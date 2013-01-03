package com.cisco.nbm.scheduler
{
	import com.cisco.util.UniqueNameFinder;
	
	import mx.collections.ArrayCollection;
	import mx.collections.Sort;
	import mx.collections.SortField;
	import mx.formatters.DateFormatter;
	
	public class ScheduleExceptionEntry 
	{
		private var _name:String;
		
		private var _nodeReferenceName:String;
		
		private var _startDate:Date;
		
		private var _endDate:Date;
		
		public static const DATE_FORMATTER:DateFormatter = new DateFormatter();
		
		[Bindable]
		public var timeValueEntries:ArrayCollection /* of DailyEntry */ = new ArrayCollection();
		
		public static const DAILY_ENTRY_PREFIX:String = "entry";
		
		public static const NEXT_ENTRY_DELTA:int = 60 * 60; // 60 minutes
		
		private var _parentSchedule:HierarchicalSchedule;
		
		public function ScheduleExceptionEntry(parentSchedule:HierarchicalSchedule):void
		{
			_parentSchedule = parentSchedule;
			
			DATE_FORMATTER.formatString = "MM/DD/YYYY";
			
			var sort:Sort = new Sort();
			sort.fields = [ new SortField("time", false, false, true) ];
			timeValueEntries.sort = sort;
			timeValueEntries.refresh();
				
		}
		
		public function set parentSchedule(value:HierarchicalSchedule):void
		{
			_parentSchedule = value;
		}
		
		public static function fromValues(parentSchedule:HierarchicalSchedule, values:Array, entries:Array):ScheduleExceptionEntry
		{
			var entry:ScheduleExceptionEntry = new ScheduleExceptionEntry(parentSchedule);
			
			entry._name = values[0];
			entry._startDate = new Date(values[1] as String);
			if ((values[2] as String).length > 0)
			{
				entry._endDate = new Date(values[2] as String);
			}
			
			entry._nodeReferenceName = values[3];
			
			for each (var tvEntry:Array in entries)
			{
				var newEntry:DailyEntry = DailyEntry.fromValues(tvEntry[0], tvEntry[1], tvEntry[2]);
				entry.timeValueEntries.addItem(newEntry);
			}
			
			return entry;
		}
		
		/**
		 * Creates a new daily entry that does not conflict with the existing 
		 * daily entries and that has a new unique name.  The entry is <b>NOT</b>
		 * added to the set of entries for this Exception so you must manually 
		 * add it to the exceptions.
		 * 
		 * @return DailyEntry The new entry that does not conflict with other
		 * 			existing entries.  
		 */
		public function createDailyEntry():DailyEntry
		{
			/*
			var coll:ArrayCollection = _schedule.metaData;
				
				if (coll.length == 0)
				{
					// TODO If no event meta, create default event meta
					throw new Error("No event meta!");
				}
				
				var firstEntry:EventMetaData = coll.getItemAt(0) as EventMetaData;
				
				var entries:ArrayCollection = control.entries;
				
				var names:Array = [];
				
				for each (var de:DailyEntry in entries)
				{
					names.push(de.name);
				}
				
				var uniqueNameFinder:UniqueNameFinder = new UniqueNameFinder();
				
				var newEntry:DailyEntry = new DailyEntry();
				newEntry.name = uniqueNameFinder.find("entry", names); 
				newEntry.value = firstEntry.value;
				newEntry.time = time * 60;
			*/
			
			
			var entry:DailyEntry = _parentSchedule.createDailyEntry();//new DailyEntry();
			
			var maxTime:int = 0;
			var names:Array /* of String */ = [];
			
			
			for each (var existingEntry:DailyEntry in timeValueEntries)
			{
				if (existingEntry.time >= maxTime)
				{
					maxTime = existingEntry.time + NEXT_ENTRY_DELTA;
				}
				
				names.push(existingEntry.name);
			}
			
			var nameFinder:UniqueNameFinder = new UniqueNameFinder();
			entry.name = nameFinder.find(DAILY_ENTRY_PREFIX, names);
			//entry.value = "";
			// Determine if the max time plus 5 minutes is too far, and if so
			// then set it to 0.
			
			if (maxTime > 24 * 60 * 60)
			{
				maxTime = 0;
			}
			
			
			entry.time = maxTime;
			
			return entry;
		}
		
		public function addDailyEntry(entry:DailyEntry):void
		{
			timeValueEntries.addItem(entry);
		}
		
		public function removeDailyEntry(entry:DailyEntry):void
		{
			var idx:int = timeValueEntries.getItemIndex(entry);
			
			if (idx != -1)
			{
				timeValueEntries.removeItemAt(idx);
			}
		}
		
		[Bindable]
		public function get name():String
		{
			return _name;
		}
		
		public function set name(value:String):void
		{
			_name = value;
		}
		
		[Bindable]
		public function set nodeReferenceName(value:String):void
		{
			_nodeReferenceName = value;
		}
		
		public function get nodeReferenceName():String
		{
			return _nodeReferenceName;
		}
		
		[Bindable]
		public function get startDate():Date
		{
			return _startDate;
		}
		
		public function set startDate(value:Date):void
		{
			_startDate = value;
		}
		
		[Bindable]
		public function set endDate(value:Date):void
		{
			_endDate = value;
		}
		
		public function get endDate():Date
		{
			return _endDate;
		}
		
		public function entriesToSummaryArray():Array /* of Object */
		{
			var array:Array = [];
			
			for each (var entry:DailyEntry in timeValueEntries)
			{
				array.push( entry.toMPXArray() );
			}
			
			return array;
		}
		
		public function toMPXStartDateString():String
		{
			return DATE_FORMATTER.format(_startDate);
		}
		
		public function toMPXEndDateString():String
		{
			return DATE_FORMATTER.format(_endDate);
		}
		
		public function toMPXSummaryEntry():Array
		{
			return [ _name, 
				DATE_FORMATTER.format(_startDate), DATE_FORMATTER.format(_endDate), 
				_name ];
		}
		
	}
}