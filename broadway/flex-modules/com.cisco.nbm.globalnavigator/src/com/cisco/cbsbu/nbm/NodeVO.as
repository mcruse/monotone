package com.cisco.cbsbu.nbm {

    import mx.collections.ArrayCollection;
	
    [Bindable]
    public dynamic class NodeVO {
	    public var id : Number;
	    public var name : String;
	    public var description : String;
	    public var managerName : String;
	    public var parent : Number;
	    public var type : String;
	    public var url : String;
	    public var displayURL : String;
	    public var label : String;
	    public var children : ArrayCollection;
	    public var parentNode : NodeVO;
	    public var isLeaf : Boolean;
        public var redirectionURL : String;
//	    public var childAdded : Boolean = false;

        public function hasChildren():Boolean {
            return !isLeaf;
        }

    } // end class
} // end package
