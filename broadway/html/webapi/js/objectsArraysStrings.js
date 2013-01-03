/* objectsArraysStrings.js */
/*
     Example File From "JavaScript and DHTML Cookbook"
     Published by O'Reilly & Associates
     Copyright 2003 Danny Goodman

$Name: mediator_3_1_2_branch $
$Id: objectsArraysStrings.js 20101 2011-03-06 16:02:15Z bhagn $
*/

function object2String(obj) {
    var val, output = "";
    if (obj) {    
        output += "{";
        for (var i in obj) {
            val = obj[i];
            switch (typeof val) {
                case ("object"):
                    if(val == null) {
                        output += i + ":" + "null,";
		    }
                    else if (val[0]) {
                        output += i + ":" + array2String(val) + ",";
                    } else {
                        output += i + ":" + object2String(val) + ",";
                    }
                    break;
                case ("string"):
                    output += i + ":'" + escape(val) + "',";
                    break;
                default:
                    output += i + ":" + val + ",";
            }
        }
        output = output.substring(0, output.length-1) + "}";
    }
    return output;
}

function array2String(array) {
    var output = "";
    if (array) {
        output += "[";
        for (var i in array) {
            val = array[i];
            switch (typeof val) {
                case ("object"):
                    if(val == null) {
			output += "null,";
		    }
                    else if (val[0]) {
                        output += array2String(val) + ",";
                    } else {
                        output += object2String(val) + ",";
                    }
                    break;
                case ("string"):
                    output += "'" + escape(val) + "',";
                    break;
                default:
                    output += val + ",";
            }
        }
        output = output.substring(0, output.length-1) + "]";
    }
    return output;
}


function string2Object(string) {
    eval("var result = " + string);
    return result;
}

function string2Array(string) {
    eval("var result = " + string);
    return result;
}
