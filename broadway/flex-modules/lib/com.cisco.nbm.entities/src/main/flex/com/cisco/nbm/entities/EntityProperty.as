package com.cisco.nbm.entities
{
	public class EntityProperty
	{
		private var _name:String;
		
		private var _type:String;
		
		private var _label:String;
		
		private var _description:String;
		
		private var _optional:Object = {};
		
		private var _value:Object;
		
		private var _overrides:Array = [];
		
		public var _input:Boolean = false;
		
		public var _output:Boolean = false;
		
		public static const COUNT_LEVELS:int = 16;
		
		[Bindable]
		public var canWrite:Boolean = true;
		
		public function EntityProperty()
		{
			
		}
		
		public function isInput():Boolean
		{
			return _input;
		}
		
		public function isOutput():Boolean
		{
			return _output;
		}
		
		[Bindable]
		public function set value(v:Object):void
		{
			this._value = v;
		}
		
		public function get value():Object
		{
			return _value;
		}
		
		public function setOverrides(dict:Object):void
		{
			for (var i:int = 0; i < COUNT_LEVELS; i++)
			{
				//_overrides["" + (i+1)] = dict[i];
			}  
		}
		
		public function get overrides():Array
		{
			return _overrides;
		}
		
		public function fromObject(object:Object):void
		{
			if (object['description'] != undefined)
			{
				_description = object['description'];
			}
			
			if (object['name'] != undefined)
			{
				_name = object['name'];
			}
			
			if (object['label'] != undefined)
			{
				_label = object['label'];
			}
			
			if (object['type'] != undefined)
			{
				_type = object['type'];
			}
			
			var tempType:String = _type.toLowerCase();
			
			if (Globals.OUTPUTS.indexOf(tempType) != -1)
			{
				_output = true;
			}
			
			else if (Globals.INPUTS.indexOf(tempType) != -1)
			{
				_input = true;
			}
			
			var defined:Array = [ 'description', 'name', 'label', 'type'];
			
			for (var key:String in object)
			{
				if (defined.indexOf(key) == -1 && key.indexOf("_") != 0)
				{
					_optional[key] = object[key];
				}
			}
		}
		
		public function get optional():Object
		{
			return _optional;
		}
		
		public function get name():String
		{
			return _name;
		}
		
		public function get type():String
		{
			return _type;
		}
		
		public function get label():String
		{
			return _label;
		}
		
		public function get description():String
		{
			return _description;
		}
		
		public function toString():String
		{
			var s:String =  "Property(name='" + _name + "', label='"+_label +"', description='"+_description+"', "
				+ "type=" + _type + ", optional={";
				
			var sep:String = "";
			for (var key:String in _optional)
			{
				s += sep + key + "=" + _optional[key];
				sep = ",";
			}
			
			s += "}]";
			
			return s;
		}
	}
}