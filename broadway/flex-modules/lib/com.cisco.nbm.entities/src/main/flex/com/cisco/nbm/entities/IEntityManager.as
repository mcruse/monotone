package com.cisco.nbm.entities
{
	import flash.events.IEventDispatcher;
	
	import mx.collections.ArrayCollection;
	
	public interface IEntityManager extends IEventDispatcher
	{
		function get entities():ArrayCollection /* of IEntity */;
	}
}