cisco = function()
{
	
}

cisco.NBMBridge = function()
{
	
}

cisco.NBMBridge = {
		widgets : {},
		
		loaded : function(id)
		{
			
			var widget = cisco.NBMBridge.widgets[id];
			
			if (widget != null)
			{
				widget.loaded();
			}
		},
		
		isReady : function()
		{
			return true;
		},
		
		createWidget : function(swfUrlStr, replaceElemIdStr, /* String */ name_id, widthStr, heightStr, flashvarsObj, parObj, attObj)
		{
			attObj.id = name_id;
			attObj.name = name_id;
			
			var widget = new NBMWidget(name_id)
			
			cisco.NBMBridge.widgets[name_id] = widget;
			
			swfobject.embedSWF(swfUrlStr,
			replaceElemIdStr, widthStr, heightStr, "9.0.0",
			false, flashvarsObj, parObj, attObj);
			
			return widget;
		},
		
		
		_addExternalInterfaceCallback : function(id, methodName)
		{
			var widget = cisco.NBMBridge.widgets[id];
			
			widget._registerCallback(methodName)
		},
		
		/**
		 *  Called from flex NBMWidget proxy to this widget proxy
		 */
		_call : function(id, methodName, args)
		{
			var widget = cisco.NBMBridge.widgets[id];
			
			if (widget != null)
			{
				widget[methodName].apply(widget, args);
			}
			else
			{
				alert("no such widget: " + id)
			}
		}
}



function NBMWidget(id)
{
	this._initialize(id)
}

NBMWidget.prototype = {
		
	ready: false,
	movie: null, 
	id: null,
	_subscription_handles : {},
	listeners: [],
	
	_registerCallback : function(methodName)
	{
		this[methodName] = function(args)
		{
			this.execute(methodName, args);
		}
	},
	
	subscribe : function(topic, methodName)
	{
		this._registerCallback(methodName);
		
		var handle = dojo.subscribe(topic, this, methodName)
		
		this._subscription_handles[topic + "_" + methodName] = handle;
		                           
		
	},
	
	unsubscribe : function(topic, methodName)
	{
		var handle = this._subscription_handles[topic + "_" + methodName];
		
		dojo.unsubscribe(handle);
	},

	_initialize: function(id)
	{
		this.id = id;
	},
	
	initialize : function()
	{
		ready = true;
		
		for (var i = 0; i < listeners.length; i++)
		{
			try
			{	
				listeners[i]()
			}
			catch (e)
			{
				alert("Error executing listener:"  + e);
			}
		}
		listeners = [];
		
	},
	
	swfObjectLoaded : function(e)
	{
		
	},
	
	addLoadedListener: function(/* Function */ listener) 
	{
		if (ready)
		{
			listener();
		}
		else
		{
			this.listeners.push(listener);
		}
	},
			
	isReady : function()
	{
		return ready;
	},
	
	execute : function(methodName, args)
	{
		this.movie[methodName](args);
	},
			
	loaded : function()
	{
		this.movie = dojo.byId(this.id);
	
		if (this.movie != null)
		{
			//this.execute("testOutside", "one");
		}
	}
	
}	

