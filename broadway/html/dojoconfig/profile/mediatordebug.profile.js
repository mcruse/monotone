dependencies = {
	layers:[
			
			//Our target mediatorlayer
			{
				name: "../dojoconfig/mediator_dojo_layer.js",
				dependencies: [
					"dojoconfig.includes.mediator_dojo_includes",
					"dijit",
					"dojox"	
					],
				layerDependencies:[
			    ]
			}
			],
	prefixes: [
		[ "dijit", "../dijit" ],
		[ "dojox", "../dojox" ],
		[ "dojoconfig", "../../html/dojoconfig" ]		
	]
}
