/*
Copyright (C) 2008 2011 Cisco Systems

This program is free software; you can redistribute it and/or         
modify it under the terms of the GNU General Public License         
as published by the Free Software Foundation; either version 2         
of the License, or (at your option) any later version.         
    
This program is distributed in the hope that it will be useful,         
but WITHOUT ANY WARRANTY; without even the implied warranty of         
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         
GNU General Public License for more details.         
    
You should have received a copy of the GNU General Public License         
along with this program; if not, write to:         
The Free Software Foundation, Inc.         
59 Temple Place - Suite 330         
Boston, MA  02111-1307, USA.         
    
As a special exception, if other files instantiate classes, templates  
or use macros or inline functions from this project, or you compile         
this file and link it with other works to produce a work based         
on this file, this file does not by itself cause the resulting         
work to be covered by the GNU General Public License. However         
the source code for this file must still be made available in         
accordance with section (3) of the GNU General Public License.         
    
This exception does not invalidate any other reasons why a work         
based on this file might be covered by the GNU General Public         
License.
*/
/* schedulesupport.js -- schedule table support for WebScheduler
Copyright (c) 2005 Richards-Zeta
$Name: mediator_3_1_2_branch $
$Id: schedulesupport.js 20101 2011-03-06 16:02:15Z bhagn $
*/
var SchedTableDebug = false;
var MAXCOLS = 8;
var EXCEPTCOL = MAXCOLS - 1;
var rowCount = 0;
var colCount = [0,0,0,0,0,0,0,0];
var currentCol = 0;
var selectCellActive = false;
var pasteOperation = 'copy';
var currentCellSelection = null;
var myDayStrings = [{name: 'sunday', column: 6},
			{name: 'monday', column: 0},
			{name: 'tuesday', column: 1},
			{name: 'wednesday', column: 2},
			{name: 'thursday', column: 3},
			{name: 'friday', column: 4},
			{name: 'saturday', column: 5}];
//add hash lookup
for(var i = 0; i < 7; i++) {
  myDayStrings[myDayStrings[i].name] = myDayStrings[i];
}

var myExceptions = null;

//schedule indices
var SCHEDULESNAME = 0;
var SCHEDULESDATA = 1;
var SCHEDULEDAYS = 0;
var SCHEDULEWEEKLY = 1;
var SCHEDULEEXCEPTIONS = 2;
var SCHEDULEDEFAULT = 3;
var DAYSNAME = 0;
var DAYSENTRYNAME = 0;
var DAYSENTRYTIME = 1;
var DAYSENTRYVALUE = 2;
var EXCEPTIONSNAME = 0;
var EXCEPTIONSENTRYNAME = 0;
var EXCEPTIONSENTRYSTART = 1;
var EXCEPTIONSENTRYEND = 2;
var EXCEPTIONSENTRYDAYSNAME = 3;

function SchedTable_log(msg) {
  if(SchedTableDebug) {
    try {
      if(parent && parent.SchedulerEditor){
        parent.msglog(msg);
      }
      else if(window.opener && window.opener.msglog != null){
        window.opener.msglog(msg);
      }
      else if(window.msglog){
        msglog(msg);
      }
    }
    catch(ex) {}
  }
}

function clearCellBackgrounds() {
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  for (i=0;i<rowCount;i++){
    for (j=0;j<MAXCOLS;j++){
      schedtable.rows[i].cells[j].setAttribute('bgColor','white');
	}
  }
}

function CellMouseoverHandler(evt){
  //window.status = 'CellMouseoverHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(!selectCellActive) {
    clearCellBackgrounds();
  }
  //elem.parentNode.parentNode.parentNode.setAttribute('bgColor','lightgrey');
  return true;
}

function CellMousemoveHandler(evt){
  //window.status = 'CellMousemoveHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myCell = elem.parentNode.parentNode.parentNode;
  if(!selectCellActive) {
    if(myCell.getAttribute('inUse') == 'true')
      myCell.setAttribute('bgColor','lightgrey');
  }
  return true;
}

function CellMouseoutHandler(evt){
  //window.status = 'CellMouseoutHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  /*if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;*/
  //var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(!selectCellActive) {
    clearCellBackgrounds();
  }
  //elem.setAttribute('bgColor','white');
  return true;
}

function CellClickHandler(evt){
  //window.status = 'CellClickHandler:';
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.stopPropagation)
    evt.stopPropagation();
  else
    evt.cancelBubble = true;
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myCell = elem.parentNode.parentNode.parentNode;
  if(myCell.getAttribute('inUse') == 'true') {
    if(!selectCellActive) {
      selectCellActive = true;
      currentCellSelection = myCell;
      myCell.setAttribute('isSelected', 'true');
      myCell.setAttribute('bgColor','lightgrey');
    }
    else {
      if(currentCellSelection == myCell) {
        selectCellActive = false;
        currentCellSelection = null;
        myCell.setAttribute('isSelected', 'false');
        myCell.setAttribute('bgColor','white');
        pasteOperation = 'copy'; //cancel pending cut operation
      }
      else {
        currentCellSelection.setAttribute('isSelected', 'false');
        currentCellSelection.setAttribute('bgColor','white');
        currentCellSelection = myCell;
        myCell.setAttribute('isSelected', 'true');
        myCell.setAttribute('bgColor','lightgrey');
      }
    }
  }
  return true;
}

function CellDblclickHandler(evt){
  //window.status = 'CellDblclickHandler:';
  return true;
}

function GetElement(element,t,element_name){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('element') &&
        elements[index].getAttribute('element') == element_name){
      e = elements[index];
      break;
    }
  }
  return e
}

function SchedTableInit() {
  SchedTable_log("SchedTableInit entered");
  var schedtable = document.createElement('table');
  schedtable.setAttribute('element','schedtable');
  schedtable.setAttribute('cols', MAXCOLS);
  schedtable.setAttribute('align','left');
  schedtable.setAttribute('cellpadding','0');
  schedtable.setAttribute('cellspacing','0');
  schedtable.setAttribute('width','700px');
  schedtable.setAttribute('frame','vsides');

  var editBody = document.getElementsByTagName('body')[0];
  editBody.appendChild(schedtable);
  //initialize (reinitialize) globals
  myExceptions = new Array();
  rowCount = 0;
  colCount = [0,0,0,0,0,0,0,0];
  currentCol = 0;
  selectCellActive = false;
  currentCellSelection = null;
}

function addSchedTableRow(index) {
  SchedTable_log("addSchedTableRow entered, index=" + index);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  schedtable.insertRow(index);
  for(var j=0;j<MAXCOLS;j++) {
    schedtable.rows[index].insertCell(j);
    schedtable.rows[index].cells[j].align = 'center';
    schedtable.rows[index].cells[j].setAttribute('valign','middle');
    if(j == MAXCOLS - 1) {
      schedtable.rows[index].cells[j].setAttribute('width','110px');
    }
    else {
      schedtable.rows[index].cells[j].setAttribute('width','64px');
    }
    schedtable.rows[index].cells[j].setAttribute('height','20px');
    schedtable.rows[index].cells[j].setAttribute('inUse', 'false');
    schedtable.rows[index].cells[j].setAttribute('isSelected', 'false');
  }
  rowCount++;
}

function deleteSchedTableRow(index) {
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  schedtable.deleteRow(index);
  rowCount--;
}

function getNewDayCell(time,val) {
      var outercontainer = document.createElement('div');
      outercontainer.setAttribute('element','outercontainer');
      outercontainer.style.position = 'relative';
      outercontainer.style.verticalAlign = 'middle';
      outercontainer.style.height = 'auto';
      outercontainer.style.width = 'auto';
      outercontainer.style.textAlign = 'center'; //inherited by children
      outercontainer.style.fontSize = '9px';
      outercontainer.style.fontFamily = 'verdana, arial, san-serif';
      outercontainer.style.top = '0';
      outercontainer.style.left = '0';
      outercontainer.style.zIndex = '0';

	  var textcontainer = document.createElement('div');
      textcontainer.setAttribute('element','textcontainer');
      textcontainer.style.position = 'relative';
      textcontainer.style.verticalAlign = 'middle';
      textcontainer.style.height = 'auto';
      textcontainer.style.width = 'auto';
      textcontainer.style.backgroundColor = 'transparent';
      textcontainer.style.top = '0';
      textcontainer.style.left = '0';
      textcontainer.style.zIndex = '1';

      var placeholderdiv = document.createElement('div');
      placeholderdiv.setAttribute('element', 'placeholder');
      //placeholderdiv.style.position = 'absolute';
      placeholderdiv.style.verticalAlign = 'middle';
      placeholderdiv.style.backgroundColor = 'transparent';
      placeholderdiv.innerHTML = 'XXXXXXXXXX';
      placeholderdiv.style.top = '0';
      placeholderdiv.style.left = '0';
      placeholderdiv.style.zIndex = '1';
      placeholderdiv.style.visibility = 'hidden';
      textcontainer.appendChild(placeholderdiv);

      var nodedisplaydiv = document.createElement('div');
      nodedisplaydiv.setAttribute('element', 'nodedisplay');
      nodedisplaydiv.style.position = 'absolute';
      nodedisplaydiv.style.verticalAlign = 'middle';
      nodedisplaydiv.style.backgroundColor = 'transparent';
      nodedisplaydiv.style.borderWidth = '0px';
      nodedisplaydiv.style.borderStyle = 'none';
      //nodedisplaydiv.style.borderCollapse = 'collapse';
      //nodedisplaydiv.style.borderColor = 'red';
      //FIXTHIS: NN doesn't require offset to style.top
      nodedisplaydiv.style.top = '0'; // offset for placeholder border
      nodedisplaydiv.style.left = '0';
      nodedisplaydiv.style.zIndex = '2';
      nodedisplaydiv.innerHTML = time + " " + val;

      textcontainer.appendChild(nodedisplaydiv);

      var infodiv = document.createElement('div');
      infodiv.setAttribute('element','info');
      infodiv.setAttribute('type','hidden');
      infodiv.setAttribute('time', time);
      infodiv.setAttribute('setpoint', val);
      infodiv.setAttribute('dialog_enabled', 'true');
      infodiv.setAttribute('dialog_active', false);
      //infodiv.style.position = 'relative';
      infodiv.style.backgroundColor = 'transparent';
      infodiv.style.top = '0';
      infodiv.style.left = '0';
      infodiv.style.height = '1';
      infodiv.style.width = '1';
      infodiv.style.zIndex = '0';
      infodiv.style.visibility = 'hidden';
      infodiv.style.display = 'none';

      outercontainer.appendChild(infodiv);

      var hitareacontainer = document.createElement('div');
      hitareacontainer.setAttribute('element','hitareacontainer');
      var browserIE = new RegExp('internet explorer','gi');
      if(browserIE.test(navigator.appName)) {
        hitareacontainer.attachEvent('ondblclick',SchedTableOpenChangeDayDialog);
        hitareacontainer.attachEvent('onclick',CellClickHandler);
        hitareacontainer.attachEvent('onmouseover',CellMouseoverHandler);
        hitareacontainer.attachEvent('onmouseout',CellMouseoutHandler);
        hitareacontainer.attachEvent('onmousemove',CellMousemoveHandler);
      }
      else {
        hitareacontainer.setAttribute('ondblclick','SchedTableOpenChangeDayDialog(event)');
        hitareacontainer.setAttribute('onclick','CellClickHandler(event)');
        hitareacontainer.setAttribute('onmouseover','CellMouseoverHandler(event)');
        hitareacontainer.setAttribute('onmouseout','CellMouseoutHandler(event)');
        hitareacontainer.setAttribute('onmousemove','CellMousemoveHandler(event)');
      }
      hitareacontainer.style.position = 'absolute';
      hitareacontainer.style.verticalAlign = 'middle';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.margin = '0px';
      hitareacontainer.style.padding = '0px';
      hitareacontainer.style.border = '0px';
      if(window.parent && window.parent.WebExpressEditor) {
  	    var mystring = "'url(" + window.parent.WebExpressProtocol + "//" + window.parent.WebExpressHostname + "/webapi/images/cleardot.gif)'";
      }
      else {
  	    var mystring = "'url(" + window.location.protocol + "//" + window.location.hostname + "/webapi/images/cleardot.gif)'";
      }
      /*var locstring = new String(window.location);
      var mystring = "'url(" + locstring.slice(0,locstring.lastIndexOf('/') + 1) + "cleardot.gif)'";*/
      hitareacontainer.style.backgroundImage = eval(mystring);
      hitareacontainer.style.backgroundRepeat = 'repeat';
      hitareacontainer.style.backgroundColor = 'transparent';
      hitareacontainer.style.top = '0';
      hitareacontainer.style.left = '0';
      hitareacontainer.style.zIndex = '3';

      var hitareadiv = document.createElement('div');
      hitareadiv.setAttribute('element', 'hitarea');
      //hitareadiv.style.position = 'absolute';
      hitareadiv.style.verticalAlign = 'middle';
      hitareadiv.style.backgroundColor = 'transparent';
      hitareadiv.innerHTML = 'XXXXXXXXXX';
      hitareadiv.style.top = '0';
      hitareadiv.style.left = '0';
      hitareadiv.style.zIndex = '0';
      hitareadiv.style.visibility = 'hidden';
      hitareacontainer.appendChild(hitareadiv);

      textcontainer.appendChild(hitareacontainer);
      outercontainer.appendChild(textcontainer);
      return outercontainer;
}

function getNewExceptCell(exceptname,start,end) {
      var outercontainer = document.createElement('div');
      outercontainer.setAttribute('element','outercontainer');
      outercontainer.style.position = 'relative';
      outercontainer.style.verticalAlign = 'middle';
      outercontainer.style.height = 'auto';
      outercontainer.style.width = 'auto';
      outercontainer.style.textAlign = 'center'; //inherited by children
      outercontainer.style.fontSize = '9px';
      outercontainer.style.fontFamily = 'verdana, arial, san-serif';
      outercontainer.style.top = '0';
      outercontainer.style.left = '0';
      outercontainer.style.zIndex = '0';

      var textcontainer = document.createElement('div');
      textcontainer.setAttribute('element','textcontainer');
      textcontainer.style.position = 'relative';
      textcontainer.style.verticalAlign = 'middle';
      textcontainer.style.height = 'auto';
      textcontainer.style.width = 'auto';
      textcontainer.style.backgroundColor = 'transparent';
      textcontainer.style.top = '0';
      textcontainer.style.left = '0';
      textcontainer.style.zIndex = '1';

      var placeholderdiv = document.createElement('div');
      placeholderdiv.setAttribute('element', 'placeholder');
      //placeholderdiv.style.position = 'absolute';
      placeholderdiv.style.verticalAlign = 'middle';
      placeholderdiv.style.backgroundColor = 'transparent';
      placeholderdiv.innerHTML = 'XXXXXXXXXX';
      placeholderdiv.style.top = '0';
      placeholderdiv.style.left = '0';
      placeholderdiv.style.zIndex = '1';
      placeholderdiv.style.visibility = 'hidden';
      textcontainer.appendChild(placeholderdiv);

      var nodedisplaydiv = document.createElement('div');
      nodedisplaydiv.setAttribute('element', 'nodedisplay');
      nodedisplaydiv.style.position = 'absolute';
      nodedisplaydiv.style.verticalAlign = 'middle';
      nodedisplaydiv.style.backgroundColor = 'transparent';
      nodedisplaydiv.style.borderWidth = '0px';
      nodedisplaydiv.style.borderStyle = 'none';
      //nodedisplaydiv.style.borderCollapse = 'collapse';
      //nodedisplaydiv.style.borderColor = 'red';
      //FIXTHIS: NN doesn't require offset to style.top
      nodedisplaydiv.style.top = '0'; // offset for placeholder border
      nodedisplaydiv.style.left = '0';
      nodedisplaydiv.style.zIndex = '2';
      nodedisplaydiv.innerHTML = exceptname;

      textcontainer.appendChild(nodedisplaydiv);

      var infodiv = document.createElement('div');
      infodiv.setAttribute('element','info');
      infodiv.setAttribute('type','hidden');
      infodiv.setAttribute('exceptname', exceptname);
      infodiv.setAttribute('startdate', start);
      infodiv.setAttribute('enddate', end);
      infodiv.setAttribute('dialog_enabled', 'true');
      infodiv.setAttribute('dialog_active', false);
      //infodiv.style.position = 'relative';
      infodiv.style.backgroundColor = 'transparent';
      infodiv.style.top = '0';
      infodiv.style.left = '0';
      infodiv.style.height = '1';
      infodiv.style.width = '1';
      infodiv.style.zIndex = '0';
      infodiv.style.visibility = 'hidden';
      infodiv.style.display = 'none';

      outercontainer.appendChild(infodiv);

      var hitareacontainer = document.createElement('div');
      hitareacontainer.setAttribute('element','hitareacontainer');
      var browserIE = new RegExp('internet explorer','gi');
      if(browserIE.test(navigator.appName)) {
        hitareacontainer.attachEvent('ondblclick',SchedTableOpenChangeExceptDialog);
        hitareacontainer.attachEvent('onclick',CellClickHandler);
        hitareacontainer.attachEvent('onmouseover',CellMouseoverHandler);
        hitareacontainer.attachEvent('onmouseout',CellMouseoutHandler);
        hitareacontainer.attachEvent('onmousemove',CellMousemoveHandler);
      }
      else {
        hitareacontainer.setAttribute('ondblclick','SchedTableOpenChangeDayDialog(event)');
        hitareacontainer.setAttribute('onclick','CellClickHandler(event)');
        hitareacontainer.setAttribute('onmouseover','CellMouseoverHandler(event)');
        hitareacontainer.setAttribute('onmouseout','CellMouseoutHandler(event)');
        hitareacontainer.setAttribute('onmousemove','CellMousemoveHandler(event)');
      }
      hitareacontainer.style.position = 'absolute';
      hitareacontainer.style.verticalAlign = 'middle';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.height = 'auto';
      hitareacontainer.style.width = 'auto';
      hitareacontainer.style.margin = '0px';
      hitareacontainer.style.padding = '0px';
      hitareacontainer.style.border = '0px';
      if(window.parent && window.parent.WebExpressEditor) {
  	    var mystring = "'url(" + window.parent.WebExpressProtocol + "//" + window.parent.WebExpressHostname + "/webapi/images/cleardot.gif)'";
      }
      else {
  	    var mystring = "'url(" + window.location.protocol + "//" + window.location.hostname + "/webapi/images/cleardot.gif)'";
      }
      /*var locstring = new String(window.location);
      var mystring = "'url(" + locstring.slice(0,locstring.lastIndexOf('/') + 1) + "cleardot.gif)'";*/
      hitareacontainer.style.backgroundImage = eval(mystring);
      hitareacontainer.style.backgroundRepeat = 'repeat';
      hitareacontainer.style.backgroundColor = 'transparent';
      hitareacontainer.style.top = '0';
      hitareacontainer.style.left = '0';
      hitareacontainer.style.zIndex = '3';

      var hitareadiv = document.createElement('div');
      hitareadiv.setAttribute('element', 'hitarea');
      //hitareadiv.style.position = 'absolute';
      hitareadiv.style.verticalAlign = 'middle';
      hitareadiv.style.backgroundColor = 'transparent';
      hitareadiv.innerHTML = 'XXXXXXXXXX';
      hitareadiv.style.top = '0';
      hitareadiv.style.left = '0';
      hitareadiv.style.zIndex = '0';
      hitareadiv.style.visibility = 'hidden';
      hitareacontainer.appendChild(hitareadiv);

      textcontainer.appendChild(hitareacontainer);
      outercontainer.appendChild(textcontainer);
      return outercontainer;
}

function addSchedTableDayCell(col,time,val) {
  SchedTable_log("addSchedTableDayCell,col=" + col + ",time=" + time + ",val=" + val);
  if(colCount[col] + 1 > rowCount) { //add new row if necessary
    addSchedTableRow(rowCount);
  }
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  var myCell = getNewDayCell(time,val);
  //var myCell = getNewDayCell(time,col + '.' + colCount[col]);
  schedtable.rows[colCount[col]].cells[col].appendChild(myCell);
  schedtable.rows[colCount[col]].cells[col].setAttribute('inUse', 'true');
  colCount[col] += 1;
}

function addSchedTableExceptCell(exceptname,start,end) {
  SchedTable_log("addSchedTableExceptCell,exceptname=" + exceptname);
  if(colCount[EXCEPTCOL] + 1 > rowCount) { //add new row if necessary
    addSchedTableRow(rowCount);
  }
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  var myCell = getNewExceptCell(exceptname,start,end);
  //var myCell = getNewDayCell(time,col + '.' + colCount[col]);
  schedtable.rows[colCount[EXCEPTCOL]].cells[EXCEPTCOL].appendChild(myCell);
  schedtable.rows[colCount[EXCEPTCOL]].cells[EXCEPTCOL].setAttribute('inUse', 'true');
  colCount[EXCEPTCOL] += 1;
}

function changeSchedTableExceptCell() {
  SchedTable_log("changeSchedTableExceptCell(), at top");
  try {
    var ielement = GetElement(DialogWin.elem,'div','info');
    ielement.setAttribute('startdate', DialogWin.newStartDate);
    if(DialogWin.newEndDate == null) {
      ielement.setAttribute('enddate', '');
    }
    else {
      ielement.setAttribute('enddate', DialogWin.newEndDate);
    }
    ielement.setAttribute('dialog_active',true);
  }
  catch(err) {
    alert('ERROR: ' + err.message + '\nPlease check node path for this widget.');
  }
}


function renameSchedTableExceptCell(exceptname) {
  SchedTable_log("renameSchedTableExceptCell(), exceptname=" + exceptname);
  try {
    var ielement = GetElement(currentCellSelection,'div','info');
    var ndelement = GetElement(currentCellSelection,'div','nodedisplay');
    ielement.setAttribute('exceptname', exceptname);
    ndelement.innerHTML = exceptname;
  }
  catch(err) {
    alert('ERROR: ' + err.message + '\nPlease check node path for this widget.');
  }
}

function deleteSchedTableDayCell() {
  if(selectCellActive) {
    if(currentCellSelection.cellIndex == currentCol) { //if cell selection in this column
      var myCell = GetElement(currentCellSelection,'div','outercontainer');
      currentCellSelection.removeChild(myCell);
      currentCellSelection.setAttribute('inUse', 'false');
      currentCellSelection.setAttribute('isSelected', 'false');
      currentCellSelection = null;
      selectCellActive = false;
      clearCellBackgrounds();
      SchedTableCleanColumn(currentCol);
      SchedTablePruneRows();
      colCount[currentCol] -= 1;
    }
  }
}

function deleteSchedTableExceptCell() {
  if(selectCellActive) {
    if(currentCellSelection.cellIndex == EXCEPTCOL) { //if cell selection in except column
      //first clear entry in myExceptions array
      var myExceptName = GetElement(currentCellSelection,'div','info').getAttribute('exceptname');
      for(var i = 0; i < myExceptions.length; i++) { //find entry in myExceptions array
        if(myExceptions[i].name == myExceptName) {
          //clear hash entry
          delete myExceptions[myExceptName];
          //remove array entry
          myExceptions.splice(i,1);
        }
      }

      //then clear entry in schedtable
      var myCell = GetElement(currentCellSelection,'div','outercontainer');
      currentCellSelection.removeChild(myCell);
      currentCellSelection.setAttribute('inUse', 'false');
      currentCellSelection.setAttribute('isSelected', 'false');
      currentCellSelection = null;
      selectCellActive = false;
      clearCellBackgrounds();
      SchedTableCleanColumn(EXCEPTCOL);
      SchedTablePruneRows();
      colCount[EXCEPTCOL] -= 1;
    }
  }
}

function deleteSchedTableExceptColumn() {
  SchedTable_log("deleteSchedTableExceptColumn() entered, colCount[EXCEPTCOL]=" + colCount[EXCEPTCOL]);
  if(selectCellActive) {
    if(currentCellSelection.cellIndex == EXCEPTCOL) { //if cell selection in this column
      currentCellSelection = null;
      selectCellActive = false;
    }
  }
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  for(var i=0;i < colCount[EXCEPTCOL];i++) {
    //first clear entry in myExceptions array
    var myExceptName = GetElement(schedtable.rows[i].cells[EXCEPTCOL],'div','info').getAttribute('exceptname');
    for(var j = 0; j < myExceptions.length; j++) { //find entry in myExceptions array
      if(myExceptions[j].name == myExceptName) {
        //clear hash entry
        delete myExceptions[myExceptName];
        //remove array entry
        myExceptions.splice(j,1);
      }
    }
    //then clear entry in schedtable
    var myContainer = GetElement(schedtable.rows[i].cells[EXCEPTCOL],'div','outercontainer');
    schedtable.rows[i].cells[EXCEPTCOL].removeChild(myContainer);
    schedtable.rows[i].cells[EXCEPTCOL].setAttribute('inUse', 'false');
    schedtable.rows[i].cells[EXCEPTCOL].setAttribute('isSelected', 'false');
  }
  SchedTablePruneRows();
  colCount[EXCEPTCOL] = 0;
}

function deleteSchedTableDayColumn() {
  SchedTable_log("deleteSchedTableDayColumn() entered, currentCol=" + currentCol + ", colCount[col]=" + colCount[currentCol]);
  if(selectCellActive) {
    if(currentCellSelection.cellIndex == currentCol) { //if cell selection in this column
      currentCellSelection = null;
      selectCellActive = false;
    }
  }
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  for(var i=0;i < colCount[currentCol];i++) {
    var myContainer = GetElement(schedtable.rows[i].cells[currentCol],'div','outercontainer');
    schedtable.rows[i].cells[currentCol].removeChild(myContainer);
    schedtable.rows[i].cells[currentCol].setAttribute('inUse', 'false');
    schedtable.rows[i].cells[currentCol].setAttribute('isSelected', 'false');
  }
  SchedTablePruneRows();
  colCount[currentCol] = 0;
}

function SchedTableCleanColumn(col) {
  SchedTable_log("SchedTableCleanColum() entered, col=" + col + ", colCount[col]=" + colCount[col]);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(colCount[col] > 1) {
    for(var i=0;i < colCount[col] - 1;i++) {
      if(schedtable.rows[i].cells[col].getAttribute('inUse') == 'false') {
        for(var j = i + 1; j <= colCount[col] - 1;j++) { //look for cell to move
          if(schedtable.rows[j].cells[col].getAttribute('inUse') == 'true') {
            var myContainer = GetElement(schedtable.rows[j].cells[col],'div','outercontainer');
            schedtable.rows[i].cells[col].appendChild(schedtable.rows[j].cells[col].removeChild(myContainer));
            schedtable.rows[i].cells[col].setAttribute('inUse', 'true');
            schedtable.rows[i].cells[col].setAttribute('isSelected',schedtable.rows[j].cells[col].getAttribute('isSelected'));
            schedtable.rows[j].cells[col].setAttribute('inUse', 'false');
            schedtable.rows[j].cells[col].setAttribute('isSelected', 'false');
            break;
          }
        }
      }
    }
  }
}

function SchedTablePruneRows() {
  SchedTable_log("SchedTablePruneRows() entered");
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  for(var i = rowCount - 1;i >= 0;i--) {
    var busy = false;
    for(var j=0;j < MAXCOLS;j++) {
      if(schedtable.rows[i].cells[j].getAttribute('inUse') == 'true') {
        busy = true;
        break;
      }
    }
    if(!busy) {
      deleteSchedTableRow(i);
    }
    else {
      break;
    }
  }
}

function SchedTableSortColumnByTime(col) {
  SchedTable_log("SchedTableSortColumnByTime() entered, col=" + col + ", colCount[col]=" + colCount[col]);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(colCount[col] > 1) {
    for(var i=0;i < colCount[col] - 1;i++) {
      var itime = GetElement(schedtable.rows[i].cells[col],'div','info').getAttribute('time');
      for(var j = i + 1; j < colCount[col];j++) { //look for cell to move
        var jtime = GetElement(schedtable.rows[j].cells[col],'div','info').getAttribute('time');
        if(jtime < itime) {
          var iCellContent = schedtable.rows[i].cells[col].removeChild(GetElement(schedtable.rows[i].cells[col],'div','outercontainer'));
          var iSelected = schedtable.rows[i].cells[col].getAttribute('isSelected');
          schedtable.rows[i].cells[col].appendChild(schedtable.rows[j].cells[col].removeChild(GetElement(schedtable.rows[j].cells[col],'div','outercontainer')));
          schedtable.rows[i].cells[col].setAttribute('isSelected',schedtable.rows[j].cells[col].getAttribute('isSelected'));
          schedtable.rows[j].cells[col].appendChild(iCellContent);
          schedtable.rows[j].cells[col].setAttribute('isSelected', iSelected);
          if(schedtable.rows[i].cells[col].getAttribute('isSelected') == 'true') {
            currentCellSelection = schedtable.rows[i].cells[col];
            schedtable.rows[i].cells[col].setAttribute('bgColor','lightgrey');
          }
          else {
            schedtable.rows[i].cells[col].setAttribute('bgColor','white');
          }
          if(schedtable.rows[j].cells[col].getAttribute('isSelected') == 'true') {
            currentCellSelection = schedtable.rows[j].cells[col];
            schedtable.rows[j].cells[col].setAttribute('bgColor','lightgrey');
          }
          else {
            schedtable.rows[j].cells[col].setAttribute('bgColor','white');
          }
          itime = jtime;
          break;
        }
      }
    }
  }
}

function SchedTableSortColumnByExceptName() {
  SchedTable_log("SchedTableSortColumnByExceptTime() entered");
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(colCount[EXCEPTCOL] > 1) {
    for(var i=0;i < colCount[EXCEPTCOL] - 1;i++) {
      var iexceptname = GetElement(schedtable.rows[i].cells[EXCEPTCOL],'div','info').getAttribute('exceptname');
      for(var j = i + 1; j < colCount[EXCEPTCOL];j++) { //look for cell to move
        var jexceptname = GetElement(schedtable.rows[j].cells[EXCEPTCOL],'div','info').getAttribute('exceptname');
        if(jexceptname < iexceptname) {
          var iCellContent = schedtable.rows[i].cells[EXCEPTCOL].removeChild(GetElement(schedtable.rows[i].cells[EXCEPTCOL],'div','outercontainer'));
          var iSelected = schedtable.rows[i].cells[EXCEPTCOL].getAttribute('isSelected');
          schedtable.rows[i].cells[EXCEPTCOL].appendChild(schedtable.rows[j].cells[EXCEPTCOL].removeChild(GetElement(schedtable.rows[j].cells[EXCEPTCOL],'div','outercontainer')));
          schedtable.rows[i].cells[EXCEPTCOL].setAttribute('isSelected',schedtable.rows[j].cells[EXCEPTCOL].getAttribute('isSelected'));
          schedtable.rows[j].cells[EXCEPTCOL].appendChild(iCellContent);
          schedtable.rows[j].cells[EXCEPTCOL].setAttribute('isSelected', iSelected);
          if(schedtable.rows[i].cells[EXCEPTCOL].getAttribute('isSelected') == 'true') {
            currentCellSelection = schedtable.rows[i].cells[EXCEPTCOL];
            schedtable.rows[i].cells[EXCEPTCOL].setAttribute('bgColor','lightgrey');
          }
          else {
            schedtable.rows[i].cells[EXCEPTCOL].setAttribute('bgColor','white');
          }
          if(schedtable.rows[j].cells[EXCEPTCOL].getAttribute('isSelected') == 'true') {
            currentCellSelection = schedtable.rows[j].cells[EXCEPTCOL];
            schedtable.rows[j].cells[EXCEPTCOL].setAttribute('bgColor','lightgrey');
          }
          else {
            schedtable.rows[j].cells[EXCEPTCOL].setAttribute('bgColor','white');
          }
          iexceptname = jexceptname;
          break;
        }
      }
    }
  }
}

function SchedTableCopyDayCell() {
  SchedTable_log("SchedTableCopyDayCell() entered");
  if(!selectCellActive)
    return;
  pasteOperation = 'copy';
}

function SchedTableCopyDayColumn(fromCol,toCol) {
  SchedTable_log("SchedTableCopyDayColumn() entered, fromCol=" + fromCol + ", toCol=" + toCol);
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  if(toCol == 99) { //copy to all columns
    for(var j=0;j < EXCEPTCOL;j++) {
      if(j != fromCol) {
        for(var i=0;i < colCount[fromCol];i++) {
          var ielement = GetElement(schedtable.rows[i].cells[fromCol],'div','info');
          addSchedTableDayCell(j,ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
        }
        SchedTableSortColumnByTime(j);
      }
    }
  }
  else { //copy to specific column
    for(var i=0;i < colCount[fromCol];i++) {
      var ielement = GetElement(schedtable.rows[i].cells[fromCol],'div','info');
      addSchedTableDayCell(toCol,ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
    }
    SchedTableSortColumnByTime(toCol);
  }
}

function SchedTableCutDayCell() {
  SchedTable_log("SchedTableCutDayCell() entered");
  if(!selectCellActive)
    return;
  pasteOperation = 'cut';
}

function SchedTableDeleteDayCell() {
  SchedTable_log("SchedTableDeleteDayCell() entered");
  deleteSchedTableDayCell();
}

function SchedTableClearDayColumn() {
  SchedTable_log("SchedTableClearDayColumn() entered");
  deleteSchedTableDayColumn();
}

function SchedTablePasteDayCell() {
  SchedTable_log("SchedTableMoveDayCell() entered");
  if(!selectCellActive)
    return;
  if(pasteOperation == 'copy') {
    var ielement = GetElement(currentCellSelection,'div','info');
    addSchedTableDayCell(currentCol,ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
    SchedTableSortColumnByTime(currentCol);
  }
  else { //cut
    var ielement = GetElement(currentCellSelection,'div','info');
    addSchedTableDayCell(currentCol,ielement.getAttribute('time'),ielement.getAttribute('setpoint'));
    SchedTableSortColumnByTime(currentCol);
    var myCellIndex = currentCellSelection.cellIndex;
    var myCell = GetElement(currentCellSelection,'div','outercontainer');
    currentCellSelection.removeChild(myCell);
    currentCellSelection.setAttribute('inUse', 'false');
    currentCellSelection.setAttribute('isSelected', 'false');
    currentCellSelection = null;
    selectCellActive = false;
    pasteOperation = 'copy';  //set to default
    clearCellBackgrounds();
    SchedTableCleanColumn(myCellIndex);
    SchedTablePruneRows();
    colCount[myCellIndex] -= 1;
  }
}

function SchedTableDeleteExceptCell() {
  SchedTable_log("SchedTableDeleteExceptCell() entered");
  deleteSchedTableExceptCell();
}

function SchedTableDuplicateExceptCell() {
  SchedTable_log("SchedTableDuplicateExceptCell() entered");
  //deleteSchedTableDayCell();
}

function SchedTableRenameExceptCell() {
  SchedTable_log("SchedTableRenameExceptCell() entered");
  if(selectCellActive) {
    SchedTable_log("SchedTableRenameExceptCell(), selectCellActive");
    if(currentCellSelection.cellIndex == EXCEPTCOL) { //if cell selection in except column
      SchedTable_log("SchedTableRenameExceptCell(), currentCellSelection.cellIndex == EXCEPTCOL");
      var newExceptName = prompt("Enter new exception name:","");
      if(newExceptName == null || newExceptName == '') {
        return;
      }
      else {
        var oldExceptName = GetElement(currentCellSelection,'div','info').getAttribute('exceptname');
        SchedTable_log("SchedTableRenameExceptCell(), myOldExceptName=" + oldExceptName);
        myExceptions[newExceptName] = myExceptions[oldExceptName];
        myExceptions[newExceptName].name = newExceptName;
	delete myExceptions[oldExceptName];
	renameSchedTableExceptCell(newExceptName);
        SchedTableSortColumnByExceptName();
      }
    }
  }
}

function SchedTableClearExceptColumn() {
  SchedTable_log("SchedTableClearExceptColumn() entered");
  deleteSchedTableExceptColumn();
}

/* dialog window support stuff */

var SchedTableNav4 = ((navigator.appName == "Netscape") && (parseInt(navigator.appVersion) == 4));

var DialogWin = new Object();

function SchedTableDeadEnd () {
  if(DialogWin.win && !DialogWin.win.closed) {
    if(DialogWin.onTop == true) {
      DialogWin.win.focus();
    }
    return false;
  }
}

var SchedTableLinkClicks;

function SchedTableDisableForms() {
  SchedTable_log("SchedTableDisableForms() entered");
  SchedTableLinkClicks = new Array();
  for(var i = 0; i < document.forms.length; i++) {
    for(var j = 0; j < document.forms[i].elements.length; j++) {
      document.forms[i].elements[j].disabled = true;
    }
  }
  for(var i = 0; i < document.links.length; i++) {
    SchedTableLinkClicks[i] = {click:document.links[i].onclick, up:null};
    SchedTableLinkClicks[i].up = document.links[i].onmouseup;
    document.links[i].onclick = SchedTableDeadEnd;
    document.links[i].onmouseup = SchedTableDeadEnd;
    document.links[i].disabled = true;
  }
  window.onfocus = SchedTableCheckModal;
  document.onclick = SchedTableCheckModal;
}

function SchedTableEnableForms() {
  SchedTable_log("SchedTableEnableForms() entered");
  for(var i = 0; i < document.forms.length; i++) {
    for(var j = 0; j < document.forms[i].elements.length; j++) {
      document.forms[i].elements[j].disabled = false;
    }
  }
  for(var i = 0; i < document.links.length; i++) {
    document.links[i].onclick = SchedTableLinkClicks[i].click;
    document.links[i].onmouseup = SchedTableLinkClicks[i].up;
    document.links[i].disabled = false;
  }
}

function BlockEvents() {
  SchedTable_log("BlockEvents() entered");
  if(SchedTableNav4) {
    window.captureEvents(Event.CLICK | Event.MOUSEDOWN | Event.MOUSEUP | Event.FOCUS);
    window.onclick = SchedTableDeadEnd;
  }
  else {
    SchedTableDisableForms();
  }
  window.onfocus = SchedTableCheckModal;
}

function UnblockEvents() {
  SchedTable_log("UnblockEvents() entered");
  if(SchedTableNav4) {
    window.releaseEvents(Event.CLICK | Event.MOUSEDOWN | Event.MOUSEUP | Event.FOCUS);
    window.onclick = null;
    window.onfocus = null;
  }
  else {
    SchedTableEnableForms();
  }
}

function SchedTableDoAddDay() {
  SchedTable_log("SchedTableDoAddDay() entered");
  addSchedTableDayCell(currentCol,DialogWin.newTime,DialogWin.newSetpoint);
  SchedTableSortColumnByTime(currentCol);
}

function SchedTableDoChangeDay() {
  SchedTable_log("SchedTableDoChangeDay() entered");
  SchedTable_log("SchedTableDoChangeDay() newTime=" + DialogWin.newTime);
  SchedTable_log("SchedTableDoChangeDay() newSetpoint=" + DialogWin.newSetpoint);
    try {
      var ielement = GetElement(DialogWin.elem,'div','info');
      var ndelement = GetElement(DialogWin.elem,'div','nodedisplay');
      var oldTime = ielement.getAttribute('time');
      ielement.setAttribute('time', DialogWin.newTime);
      ielement.setAttribute('setpoint', DialogWin.newSetpoint);
      ielement.setAttribute('dialog_active',true);
      ndelement.innerHTML = DialogWin.newTime + " " + DialogWin.newSetpoint;
      if(oldTime != DialogWin.newTime) {
        SchedTableSortColumnByTime(DialogWin.elem.parentNode.cellIndex);
      }
    }
    catch(err) {
      alert('ERROR: ' + err.message + '\nPlease check node path for this widget.');
    }
}

function SchedTableDoAddExcept() {
  SchedTable_log("SchedTableDoAddExcept() entered");
  SchedTable_log("SchedTableDoAddExcept() DialogWin.newExceptName=" + DialogWin.newExceptName);
  SchedTable_log("SchedTableDoAddExcept() DialogWin.newStartDate=" + DialogWin.newStartDate);
  SchedTable_log("SchedTableDoAddExcept() DialogWin.newEndDate=" + DialogWin.newEndDate);
  var myExceptionEnd = DialogWin.newEndDate;
  if(myExceptionEnd == null)
    myExceptionEnd = '';
  addSchedTableExceptCell(DialogWin.newExceptName,DialogWin.newStartDate,myExceptionEnd);
  SchedTableSortColumnByExceptName();
  if(DialogWin.newExceptSchedule != null)
    SchedTable_log("SchedTableDoAddExcept() DialogWin.newExceptSchedule=" + array2String(DialogWin.newExceptSchedule));
  var myExceptionDay = new Object();
  myExceptionDay.name = DialogWin.newExceptName;
  if(DialogWin.newExceptSchedule == null) {
    myExceptionDay.entries = null;
  }
  else {
    var myExceptionDayEntries = new Array();
    for(var i = 0; i < DialogWin.newExceptSchedule.length; i++) {
      var myNewEntry = new Array();
      myNewEntry.push(DialogWin.newExceptSchedule[i][0]);
      myNewEntry.push(DialogWin.newExceptSchedule[i][1]);
      myExceptionDayEntries.push(myNewEntry);
    }
    myExceptionDay.entries = myExceptionDayEntries;
  }
  var newLen = myExceptions.push(myExceptionDay);
  myExceptions[DialogWin.newExceptName] = myExceptions[newLen - 1]; //make new array object hash accessable
}

function SchedTableDoChangeExcept() {
  SchedTable_log("SchedTableDoChangeExcept() entered");
  SchedTable_log("SchedTableDoChangeExcept() DialogWin.newExceptName=" + DialogWin.newExceptName);
  SchedTable_log("SchedTableDoChangeExcept() DialogWin.newStartDate=" + DialogWin.newStartDate);
  SchedTable_log("SchedTableDoChangeExcept() DialogWin.newEndDate=" + DialogWin.newEndDate);
  changeSchedTableExceptCell();
  if(DialogWin.newExceptSchedule != null)
    SchedTable_log("SchedTableDoChangeExcept() DialogWin.newExceptSchedule=" + array2String(DialogWin.newExceptSchedule));
  if(DialogWin.newExceptSchedule == null) {
    myExceptions[DialogWin.newExceptName].entries = null;
  }
  else {
    var myExceptionDayEntries = new Array();
    for(var i = 0; i < DialogWin.newExceptSchedule.length; i++) {
      var myNewEntry = new Array();
      myNewEntry.push(DialogWin.newExceptSchedule[i][0]);
      myNewEntry.push(DialogWin.newExceptSchedule[i][1]);
      myExceptionDayEntries.push(myNewEntry);
    }
    myExceptions[DialogWin.newExceptName].entries = myExceptionDayEntries;
  }
}

function SchedTableOpenAddDayDialog() {
  SchedTable_log("SchedTableOpenAddDayDialog() entered");
  SchedTableOpenDialog('day','add',null);
}

function SchedTableOpenAddExceptDialog() {
  SchedTable_log("SchedTableOpenAddExceptDialog() entered");
  SchedTableOpenDialog('except','add',null);
}

function SchedTableOpenChangeExceptDialog(evt) {
  SchedTable_log("SchedTableOpenChangeExceptDialog() entered");
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.detail) {
    SchedTable_log("SchedTableOpenChangeExceptDialog(), evt.detail=" + evt.detail);
  }
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myContainer = elem.parentNode.parentNode; //outercontainer div of SchedTable widget
  SchedTable_log("SchedTableOpenChangeExceptDialog(), myContainer element = " + myContainer.getAttribute('element'));
  SchedTableOpenDialog('except','change',myContainer);
}

function SchedTableOpenChangeDayDialog(evt) {
  SchedTable_log("SchedTableOpenChangeDayDialog() entered");
  evt = (evt) ? evt : ((event) ? event : null);
  if(evt.detail) {
    SchedTable_log("SchedTableOpenChangeDayDialog(), evt.detail=" + evt.detail);
  }
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myContainer = elem.parentNode.parentNode; //outercontainer div of SchedTable widget
  SchedTable_log("SchedTableOpenChangeDayDialog(), myContainer element = " + myContainer.getAttribute('element'));
  SchedTableOpenDialog('day','change',myContainer);
}

function SchedTableOpenDialog(type,cmd,container) {
  /*var ielement = GetElement(container,'div','info');
  if(ielement.getAttribute('dialog_enabled') == 'false') {
    SchedTable_log("SchedTableOpenDialog(), early return, dialog_enabled=false");
    return; //return if dialog disabled
  }*/
  if(!DialogWin.win || (DialogWin.win && DialogWin.win.closed)) {
    SchedTable_log("SchedTableOpenDialog(), window doesn't exist or is closed");
    DialogWin.onTop = true;
    DialogWin.cmd = cmd;
    DialogWin.elem = container;
    if(type == 'day') {
      DialogWin.url = '/webapi/editday.htm';
      DialogWin.width = 240;
      DialogWin.height = 200;
    }
    else {
      DialogWin.url = '/webapi/editexcept.htm';
      DialogWin.width = 650;
      DialogWin.height = 370;
    }
    DialogWin.addDayFunc = SchedTableDoAddDay;
    DialogWin.changeDayFunc = SchedTableDoChangeDay;
    DialogWin.addExceptFunc = SchedTableDoAddExcept;
    DialogWin.changeExceptFunc = SchedTableDoChangeExcept;
    DialogWin.args = '';
    DialogWin.newDate = '';
    DialogWin.newTime = '';
    DialogWin.newSetpoint = '';
    DialogWin.newExceptName = '';
    DialogWin.newStartDate = '';
    DialogWin.newEndDate = '';
    DialogWin.newExceptSchedule = null;
    DialogWin.name = (new Date()).getSeconds().toString();
    if(parent.screenX) { //Navigator 4+
      SchedTable_log("SchedTableOpenDialog(), parent.screenX defined, Navigator branch taken");
      DialogWin.left = parent.screenX +
        ((parent.outerWidth - DialogWin.width) / 2);
      DialogWin.top = parent.screenY +
        ((parent.outerHeight - DialogWin.height) / 2);
      if(DialogWin.type = 'except')
        DialogWin.top += 80; //move exception window down an additional 80px
      var attr = "screenX=" + DialogWin.left +
        ",screenY=" + DialogWin.top + ",resizable=no,width=" +
        DialogWin.width + ",height=" + DialogWin.height;
    }
    else if(parent.screenLeft) { //Windows IE5+
      SchedTable_log("SchedTableOpenDialog(), parent.screenLeft defined, Windows IE branch taken");
      var CSSCompat = (document.compatMode && document.compatMode != "BackCompat");
      SchedTable_log("SchedTableOpenDialog(), CSSCompat=" + CSSCompat);
      parent.outerWidth = (CSSCompat) ? parent.document.body.parentElement.clientWidth :
        parent.document.body.clientWidth;
      parent.outerHeight = (CSSCompat) ? parent.document.body.parentElement.clientHeight :
        parent.document.body.clientHeight;
      parent.outerHeight -= 80;
      DialogWin.left = parseInt(parent.screenLeft +
        ((parent.outerWidth - DialogWin.width) / 2));
      DialogWin.top = parseInt(parent.screenTop +
        ((parent.outerHeight - DialogWin.height) / 2));
      if(DialogWin.type = 'except')
        DialogWin.top += 80; //move exception window down an additional 80px
      var attr = "left=" + DialogWin.left +
        ",top=" + DialogWin.top + ",resizable=no,width=" +
        DialogWin.width + ",height=" + DialogWin.height;
    }
    else {
      SchedTable_log("SchedTableOpenDialog(), generic branch taken");
      DialogWin.left = (screen.width - DialogWin.width) / 2;
      DialogWin.top = (screen.height - DialogWin.height) / 2;
      var attr = "left=" + DialogWin.left + ",top=" +
        DialogWin.top + ",resizable=no,width=" + DialogWin.width +
        ",height=" + DialogWin.height;
    }
    SchedTable_log("SchedTableOpenDialog(), after attr calc");
    if(!DialogWin.win){
      SchedTable_log("SchedTableOpenDialog(), win not defined");
    }
    else {
      SchedTable_log("SchedTableOpenDialog(), win defined");
    }
    SchedTable_log("SchedTableOpenDialog(), before window.open(), url=" + DialogWin.url +
      ", name=" + DialogWin.name + ", attr=" + attr);
    DialogWin.win = window.open(DialogWin.url, DialogWin.name, attr);
    SchedTable_log("SchedTableOpenDialog(), after window.open(), DialogWin.win.name=" + DialogWin.win.name);
    setTimeout("DialogWin.win.focus()", 250);
  }
  else {
    if(DialogWin.onTop == true) {
      setTimeout("DialogWin.win.focus()", 250);
    }
  }
}

function SchedTableCheckModal() {
  SchedTable_log("SchedTableCheckModal() entered");
  setTimeout("SchedTableFinishCheckModal()", 250);
  return true;
}

function SchedTableFinishCheckModal() {
  SchedTable_log("SchedTableFinishCheckModal() entered");
  if(DialogWin.win && !DialogWin.win.closed) {
    if(DialogWin.onTop == true) {
      SchedTable_log("SchedTableFinishCheckModal(), before focus");
      DialogWin.win.focus();
      SchedTable_log("SchedTableFinishCheckModal(), after focus");
    }
  }
}

function mySaveCompletion() {
  SchedTable_log("mySaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
  //alert("mySaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
}

function SchedNode(mediator,path){
  this.mediator = mediator;
  this.path = path;
}

SchedNode.prototype.get_summary = function(completionHandlerName){
  var rt = "";
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("get_summary");
  xml = msg.xml();
  if(arguments.length == 1) { //asynchronous
    SchedTable_log("SchedNode.get_summary(), asynchronous");
    request = new MediatorXMLRPCRequest(completionHandlerName);
    request.create();
    request.open();
    return request.send(xml);
  }
  else { //synchronous
    SchedTable_log("SchedNode.get_summary(), synchronous");
    request = new MediatorXMLRPCRequest();
    request.create();
    request.open();
    rt = request.send(xml);
    return rt;
  }
};

SchedNode.prototype.set_summary = function(summary, completionHandlerName, changeHandlerName){
  var rt = "";
  var xml = "";
  var request = null;
  var method =  "rna_xmlrpc2:invoke";

  var msg = new XMLRPCMessage(method);
  msg.addParameter(this.mediator.session);
  msg.addParameter(this.path);
  msg.addParameter("set_summary");
  msg.addParameter(summary);
  xml = msg.xml();
  SchedTable_log("SchedNode.set_summary(), xml=" + xml);
  if(arguments.length >= 2) { //asynchronous
    SchedTable_log("SchedNode.set_summary(), asynchronous");
    request = new MediatorXMLRPCRequest(completionHandlerName);
    if(arguments.length == 3) {
      request.setChangeHandler(changeHandlerName);
    }
    request.create();
    request.open();
    return request.send(xml);
  }
  else { //synchronous
    SchedTable_log("SchedNode.set_summary(), synchronous");
    request = new MediatorXMLRPCRequest();
    request.create();
    request.open();
    rt = request.send(xml);
    return rt;
  }
};

function SchedTable_save(filename){
  var msg;
  msg = "Do you really want to save?";
  if(confirm(msg)){
    //do async PUT of file using XMLRPC interface
    Scheduler_request = null; //cleanup any previous request
    Scheduler_request = new MediatorXMLRPCRequest("Scheduler_reload");
    Scheduler_request.setChangeHandler(SchedTable_save_status);
    var loc = window.location;
    var url = loc.protocol + '//' + loc.host + '/' + filename;
    Scheduler_request.setURL(url);
    Scheduler_request.setMethod("PUT");
    Scheduler_request.create();
    Scheduler_request.open();
    Scheduler_request.send(html);

    //Set all the borders back
    for(var i=0;i<widgets.length;i++){
      widgets[i].style.border = WIDGET_BORDER ;
    }
    return true;
  }
  else{
    SchedTable_msg('Save Canceled');
    return false;
  }
}

function SchedTable_reload(){
  //alert("File save complete");
}

function SchedTable_msg(msg) {
  SchedTable_log("SchedTable_msg, msg=" + msg);
  parent.Scheduler_msg(msg);
}

function SchedTable_save_status(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
     SchedTable_log("SchedTable_save_status(), readyState=" + currentState);
    if (currentState == 4){
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204
      var currentStatus = this.request.objXMLHTTP.status;
      SchedTable_log("SchedTable_save_status(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        SchedTable_msg('Schedule "'+  SCHEDULEUPDATENAME + '" was saved succesfully');
        SchedTable_updateScheduleNameDisplay(SCHEDULEUPDATENAME);
        SchedTable_updateScheduleName(SCHEDULEUPDATENAME);
      }
      else if(currentStatus == 201){
        SchedTable_msg('New schedule was created!');
        SchedTable_updateScheduleNameDisplay(SCHEDULEUPDATENAME);
        SchedTable_updateScheduleName(SCHEDULEUPDATENAME);
      }
      else{
        if(HTTP_ERRORS[currentStatus] != null){
          SchedTable_msg('Error: Schedule was not saved!<br>');
          SchedTable_msg(HTTP_ERRORS[currentStatus]);
        }
        else{
          SchedTable_msg('Error: Schedule was not saved!<br>');
          SchedTable_msg('Status Code:' + currentStatus);
        }
      }
      if(this.request.bAsync == true) {
        SchedTable_log("SchedTable_save_status(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    SchedTable_log("SchedTable_save_status(), error: " + ex.name + ", " + ex.description);
  }
}

function SchedTable_delete_status(){
  try {
    var currentState = this.request.objXMLHTTP.readyState;
     SchedTable_log("SchedTable_delete_status(), readyState=" + currentState);
    if (currentState == 4){
      // ### Hack ###
      // for some reasone IE comes back with a reponse status as 1223,
      // supposed to be 200 or 204
      var currentStatus = this.request.objXMLHTTP.status;
      SchedTable_log("SchedTable_delete_status(), status=" + currentStatus);
      if (currentStatus == 200 || currentStatus == 204 || currentStatus == 1223) {
        SchedTable_msg('Schedule "'+  SCHEDULEUPDATENAME + '" was deleted successfully');
        SchedTable_updateScheduleNameDisplay('');
        SchedTable_updateScheduleName('NEWSCHEDULE');
      }
      else{
        if(HTTP_ERRORS[currentStatus] != null){
          SchedTable_msg('Error: Schedule was not deleted!<br>');
          SchedTable_msg(HTTP_ERRORS[currentStatus]);
        }
        else{
          SchedTable_msg('Error: Schedule was not deleted!<br>');
          SchedTable_msg('Status Code:' + currentStatus);
        }
      }
      if(this.request.bAsync == true) {
        SchedTable_log("SchedTable_delete_status(), this.request.completionhandlername=" + this.request.completionhandlername);
        eval(this.request.completionhandlername).call(this.request);
        this.request = null; //release global request object
        this.inuse = false;
      }
    }
  } //end try
  catch(ex) {
    SchedTable_log("SchedTable_delete_status(), error: " + ex.name + ", " + ex.description);
  }
}

function SchedTable_populateDays() {
  SchedTable_log("SchedTable_populateDays entered");
  //SchedTable_log("SchedTable_populateDays, mySchedArray typeof(mySchedArray)=" + typeof(mySchedArray));
  //SchedTable_log("SchedTable_populateDays, mySchedArray typeof(mySchedArray[SCHEDULEDAYS])=" + typeof(mySchedArray[SCHEDULEDAYS]));
  SchedTable_log("SchedTable_populateDays, mySchedArray[SCHEDULEDAYS].length=" + mySchedArray[SCHEDULEDAYS].length);
  for(var i=0;i < mySchedArray[SCHEDULEDAYS].length;i++) { //for each schedule day
    var myDayName = mySchedArray[SCHEDULEDAYS][i][DAYSNAME];
    if(myDayStrings[myDayName]) { //if weekly schedule day
      currentCol = myDayStrings[myDayName].column;
      SchedTable_log("SchedTable_populateDays, processing " + myDayStrings[myDayName].name);
      //SchedTable_log("SchedTable_populateDays, entry type=" + typeof(mySchedArray[0][i][1]));
      SchedTable_log("SchedTable_populateDays, mySchedArray[SCHEDULEDAYS][" + i + "].length=" + mySchedArray[SCHEDULEDAYS][i].length);
      if(mySchedArray[SCHEDULEDAYS][i].length > 1) {
        for(var j=1;j < mySchedArray[SCHEDULEDAYS][i].length;j++) {
          SchedTable_log("SchedTable_populateDays, processing " + mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYNAME]);
          addSchedTableDayCell(currentCol,mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYTIME],mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYVALUE]);
          SchedTable_log("SchedTable_populateDays, after addSchedTableDayCell, i=" + i + ", j=" + j);
        }
        SchedTableSortColumnByTime(currentCol);
      }
      else {
        SchedTable_log("SchedTable_populateDays, no entries");
      }
    } //end if weekly schedule day
    else { //exception day
      SchedTable_log("SchedTable_populateDays, processing exception " + myDayName);
      myExceptionDay = new Object();
      myExceptionDay.name = myDayName;
      SchedTable_log("SchedTable_populateDays, mySchedArray[SCHEDULEDAYS][" + i + "].length=" + mySchedArray[SCHEDULEDAYS][i].length);
      if(mySchedArray[SCHEDULEDAYS][i].length > 1) { //if there are entries
        var myExceptionDayEntries = new Array();
        for(var j=1;j < mySchedArray[SCHEDULEDAYS][i].length;j++) {
          SchedTable_log("SchedTable_populateDays, processing " + mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYNAME]);
          var myNewEntry = new Array();
          myNewEntry.push(mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYTIME]);
          myNewEntry.push(mySchedArray[SCHEDULEDAYS][i][j][DAYSENTRYVALUE]);
          myExceptionDayEntries.push(myNewEntry);
        }
        myExceptionDay.entries = myExceptionDayEntries;
      }
      else {
        SchedTable_log("SchedTable_populateDays, no entries");
        myExceptionDay.entries = null;
      }
      var newLen = myExceptions.push(myExceptionDay);
      myExceptions[myDayName] = myExceptions[newLen - 1]; //make new array object hash accessable
    }
  }// end for each schedule day
}

function SchedTable_populateExceptions() {
  SchedTable_log("SchedTable_populateExceptions entered");
  SchedTable_log("SchedTable_populateExceptions, mySchedArray[SCHEDULEEXCEPTIONS].length=" + mySchedArray[SCHEDULEEXCEPTIONS].length);
  if(mySchedArray[SCHEDULEEXCEPTIONS].length > 0) {
    SchedTable_log("SchedTable_populateExceptions, mySchedArray[SCHEDULEEXCEPTIONS][0].length=" + mySchedArray[SCHEDULEEXCEPTIONS][0].length);
    if(mySchedArray[SCHEDULEEXCEPTIONS][0].length > 2) {
      for(var i=1;i < mySchedArray[SCHEDULEEXCEPTIONS][0].length - 1;i++) { //for each exception
        var myExceptionName = mySchedArray[SCHEDULEEXCEPTIONS][0][i][EXCEPTIONSENTRYNAME];
        SchedTable_log("SchedTable_populateExceptions, processing " + myExceptionName);
        SchedTable_log("SchedTable_populateExceptions, mySchedArray[SCHEDULEEXCEPTIONS][0][" + i + "].length=" + mySchedArray[SCHEDULEEXCEPTIONS][0][i].length);
        var myExceptionStart = mySchedArray[SCHEDULEEXCEPTIONS][0][i][EXCEPTIONSENTRYSTART];
        var myExceptionEnd = mySchedArray[SCHEDULEEXCEPTIONS][0][i][EXCEPTIONSENTRYEND];
        if(myExceptionEnd == null)
	  myExceptionEnd = '';
        addSchedTableExceptCell(myExceptionName,myExceptionStart,myExceptionEnd);
        SchedTable_log("SchedTable_populateExceptions, after addSchedTableExceptCell, i=" + i);
      }//end for each exception
      SchedTableSortColumnByExceptName();
    }
  }
}

var mySchedArray = null;
var mySchedHolderArray = null;
var myNewSchedHolderArray = null;

function SchedTable_load() {
  SchedTable_log("SchedTable_load() entered");
  SchedTableInit();
  window.setTimeout("SchedTable_loadPhase2()",0);
}

function SchedTable_loadPhase2() {
  SchedTable_log("SchedTable_loadPhase2() entered");
  if(parent.SCHEDULENAME == 'NEWSCHEDULE') {
    SchedTable_msg('Initialization complete');
  }
  else {
    SchedTable_msg('Loading "' + parent.SCHEDULENAME + '" schedule...');
    parent.Scheduler_updateScheduleNameDisplay(parent.SCHEDULENAME);
    SchedTable_getSchedFromMediator();
  }
}

function SchedTable_getCompletion() {
  SchedTable_log("SchedTable_getCompletion() entered");
  mySchedArray = this.result;
  SchedTable_log("SchedTable_getCompletion, mySchedArray=" + array2String(mySchedArray));
  SchedTable_msg("");
  SchedTable_populateDays();
  SchedTable_populateExceptions();
}

function SchedTable_cleanScheduleHolder(compareStr) {
  SchedTable_log("SchedTable_cleanScheduleHolder() entered");
  var myTempArray = new Array();
  for(var i = 0; i < mySchedHolderArray.length; i++) {
    SchedTable_log("SchedTable_cleanScheduleHolder(), mySchedHolderArray[" + i + "][SCHEDULESNAME]=" + mySchedHolderArray[i][SCHEDULESNAME]);
    if(!(mySchedHolderArray[i][SCHEDULESNAME] == compareStr)) {
      myTempArray.push(mySchedHolderArray[i]);
    }
  }
  return myTempArray;
}

function SchedTable_addCompletion() {
  SchedTable_log("SchedTable_addCompletion() entered");
  mySchedHolderArray = this.result;
  SchedTable_log("SchedTable_addCompletion, mySchedHolderArray=" + array2String(mySchedHolderArray));
  var myCompareStr = parent.SCHEDULEPREFIX + SCHEDULEUPDATENAME;
  myNewSchedHolderArray = SchedTable_cleanScheduleHolder(myCompareStr);
  var mySaveArray = SchedTable_buildArrayForSave();
  mySaveArray.unshift(myCompareStr);
  myNewSchedHolderArray.push(mySaveArray);
  var mySchedPath = parent.SCHEDULEHOLDER;
  SchedTable_log("SchedTable_addCompletion(), mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  SchedTable_log("SchedTable_addCompletion(), myNewSchedHolderArray=" + array2String(myNewSchedHolderArray));
  //do async PUT of schedules using XMLRPC interface
  mySchedNode.set_summary(myNewSchedHolderArray,SchedTable_addSaveCompletion,SchedTable_save_status);
}

function SchedTable_addSaveCompletion() {
  SchedTable_log("SchedTable_addSaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
  //alert("SchedTable_addSaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
}

function SchedTable_deleteCompletion() {
  SchedTable_log("SchedTable_deleteCompletion() entered");
  mySchedHolderArray = this.result;
  SchedTable_log("SchedTable_deleteCompletion, mySchedHolderArray=" + array2String(mySchedHolderArray));
  var myCompareStr = parent.SCHEDULEPREFIX + SCHEDULEUPDATENAME;
  myNewSchedHolderArray = SchedTable_cleanScheduleHolder(myCompareStr);
  var mySchedPath = parent.SCHEDULEHOLDER;
  SchedTable_log("SchedTable_deleteCompletion(), mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  SchedTable_log("SchedTable_deleteCompletion(), myNewSchedHolderArray=" + array2String(myNewSchedHolderArray));
  //do async PUT of schedules using XMLRPC interface
  mySchedNode.set_summary(myNewSchedHolderArray,SchedTable_deleteSaveCompletion,SchedTable_delete_status);
}

function SchedTable_updateScheduleNameDisplay(name) {
  parent.Scheduler_updateScheduleNameDisplay(name);
}

function SchedTable_updateScheduleName(name) {
  parent.SCHEDULENAME = name;
}

function SchedTable_deleteSaveCompletion() {
  SchedTable_log("SchedTable_deleteSaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
  //alert("SchedTable_addSaveCompletion(), this.objXMLHTTP.responseText=" + this.objXMLHTTP.responseText);
}

var MEDIATOR = null;

function SchedTable_getSchedFromMediator() {
  SchedTable_log("SchedTable_getSchedFromMediator() entered");
  if(MEDIATOR == null) { //login if necessary
    MEDIATOR = new Mediator();
    var page_properties = new PageProperties(MEDIATOR);
    MEDIATOR.login();
  }

  var mySchedPath = parent.SCHEDULEHOLDER + '/' + parent.SCHEDULEPREFIX + parent.SCHEDULENAME;
  SchedTable_log("SchedTable_getSchedFromMediator, mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  //document.getElementById('sumdisplay').value = array2String(mySchedNode.get_summary());
  mySchedNode.get_summary(SchedTable_getCompletion);
  //return mySchedNode.get_summary();
}

var SCHEDULEUPDATENAME = '';
function SchedTable_saveSchedToMediator() {
  SchedTable_log("SchedTable_saveSchedToMediator() entered");
  if(MEDIATOR == null) { //login if necessary
    MEDIATOR = new Mediator();
    var page_properties = new PageProperties(MEDIATOR);
    MEDIATOR.login();
  }

  SCHEDULEUPDATENAME = parent.SCHEDULENAME;
  var mySaveArray = SchedTable_buildArrayForSave();
  var mySchedPath = parent.SCHEDULEHOLDER + '/' + parent.SCHEDULEPREFIX + parent.SCHEDULENAME;
  SchedTable_log("SchedTable_getSchedFromMediator, mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  //do async PUT of schedule using XMLRPC interface
  mySchedNode.set_summary(mySaveArray,mySaveCompletion,SchedTable_save_status);
  //return mySchedNode.set_summary(mySaveArray);
}

function SchedTable_deleteSchedFromMediator() {
  SchedTable_log("SchedTable_deleteSchedFromMediator() entered");
  if(MEDIATOR == null) { //login if necessary
    MEDIATOR = new Mediator();
    var page_properties = new PageProperties(MEDIATOR);
    MEDIATOR.login();
  }

  SCHEDULEUPDATENAME = parent.SCHEDULENAME;
  var mySchedPath = parent.SCHEDULEHOLDER;
  SchedTable_log("SchedTable_deleteSchedFromMediator, mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  //do async GET of schedules using XMLRPC interface
  mySchedNode.get_summary(SchedTable_deleteCompletion);
  //return mySchedNode.get_summary();
}

function SchedTable_addSchedToMediator(schedname) {
  SchedTable_log("SchedTable_addSchedToMediator() entered");
  if(MEDIATOR == null) { //login if necessary
    MEDIATOR = new Mediator();
    var page_properties = new PageProperties(MEDIATOR);
    MEDIATOR.login();
  }

  SCHEDULEUPDATENAME = schedname;
  var mySchedPath = parent.SCHEDULEHOLDER;
  SchedTable_log("SchedTable_addSchedToMediator, mySchedPath=" + mySchedPath);
  var mySchedNode = new SchedNode(MEDIATOR,mySchedPath);
  //do async GET of schedules using XMLRPC interface
  mySchedNode.get_summary(SchedTable_addCompletion);
  //return mySchedNode.get_summary();
}

function SchedTable_buildArrayForSave() {
  SchedTable_log("SchedTable_buildArrayForSave() entered");
  var saveArray = new Array(4);
  saveArray[0] = SchedTable_buildDaysForSave();
  saveArray[1] = SchedTable_buildWeeklyForSave();
  saveArray[2] = SchedTable_buildExceptionsForSave();
  saveArray[3] = 'exceptions';
  SchedTable_log("SchedTable_buildArrayForSave(), saveArray=" + array2String(saveArray));
  return saveArray;
}

function SchedTable_buildDaysForSave() {
  SchedTable_log("SchedTable_buildDaysForSave() entered");
  //var myDayStrings = ['monday','tuesday','wednesday','thursday','friday','saturday','sunday'];
  var myDays = new Array();
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  //process weekly days
  for(var i=0;i<7;i++){
    SchedTable_log("SchedTable_buildDaysForSave(), weekly days i=" + i);
    var myDay = new Array();
    myDay.push(myDayStrings[i].name);
    if(colCount[myDayStrings[i].column] > 0) {
      for(var j=0;j<colCount[myDayStrings[i].column];j++) {
        SchedTable_log("SchedTable_buildDaysForSave(), weekly days j=" + j);
        var myDayEntry = new Array(3);
        myDayEntry[0] = 'entry' + j;
        var ielement = GetElement(schedtable.rows[j].cells[myDayStrings[i].column],'div','info');
        myDayEntry[1] = ielement.getAttribute('time');
        myDayEntry[2] = ielement.getAttribute('setpoint');
        myDay.push(myDayEntry);
      }
    }
    /*else {
      myDay.push(null);
    }*/
    myDays.push(myDay);
    SchedTable_log("SchedTable_buildArrayForSave(), myDays=" + array2String(myDays));
  }
  //process exception days
  for(var i=0;i < myExceptions.length;i++) {
    SchedTable_log("SchedTable_buildDaysForSave(), exception days i=" + i);
    var myDay = new Array();
    myDay.push(myExceptions[i].name);
    if(myExceptions[i].entries != null) {
      SchedTable_log("SchedTable_buildDaysForSave(), myExceptions[i].entries=" + array2String(myExceptions[i].entries));
      for(var j=0;j < myExceptions[i].entries.length;j++) {
        SchedTable_log("SchedTable_buildDaysForSave(), exception days j=" + j);
        var myDayEntry = new Array(3);
        myDayEntry[0] = 'entry' + j;
        myDayEntry[1] = myExceptions[i].entries[j][0];
        myDayEntry[2] = myExceptions[i].entries[j][1];
        myDay.push(myDayEntry);
      }
    }
    /*else {
      myDay.push(null);
    }*/
    myDays.push(myDay);
    SchedTable_log("SchedTable_buildArrayForSave(), myDays=" + array2String(myDays));
  }
  //return mySchedArray[SCHEDULEDAYS];
  return myDays;
}

function SchedTable_buildWeeklyForSave() {
  SchedTable_log("SchedTable_buildWeeklyForSave() entered");
  //return mySchedArray[SCHEDULEWEEKLY];
  return [['weekly_schedule', ['sunday','monday','tuesday','wednesday','thursday','friday','saturday']]];
}

function SchedTable_buildExceptionsForSave() {
  SchedTable_log("SchedTable_buildExceptionsForSave() entered");
  var myExceptions = new Array();
  var editBody = document.getElementsByTagName('body')[0];
  var schedtable = GetElement(editBody,'table','schedtable');
  //add 'exceptions' in first array location
  myExceptions.push('exceptions');
  //process exceptions
  for(var i=0;i < colCount[EXCEPTCOL];i++) {
    var ielement = GetElement(schedtable.rows[i].cells[EXCEPTCOL],'div','info');
    var myException = new Array();
    var myExceptName = ielement.getAttribute('exceptname');
    SchedTable_log("SchedTable_buildExceptionsForSave(), processing i=" + i + ', myExceptName=' + myExceptName);
    myException.push(myExceptName);
    myException.push(ielement.getAttribute('startdate'));
    var myEndDate = ielement.getAttribute('enddate');
    if(myEndDate.length == 0) {
      //dil ... myException.push(null);
      myException.push("");
    }
    else {
      myException.push(myEndDate);
    }
    myException.push(myExceptName);
    myExceptions.push(myException);
  }
  //add 'weekly_schedule' in last array location
  myExceptions.push('weekly_schedule');
  //return mySchedArray[SCHEDULEEXCEPTIONS];
  var myRetArray = new Array();
  myRetArray.push(myExceptions);
  return myRetArray;
}

