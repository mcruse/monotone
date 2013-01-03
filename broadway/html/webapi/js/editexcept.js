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
/* editexcept.js -- support for exception editing in WebScheduler
 * $Name: mediator_3_1_2_branch $
 * $Id: editexcept.js 20101 2011-03-06 16:02:15Z bhagn $
 */
var EditExceptDebug = false;
var IFRAMENAME = '';
var IFRAME = null;
var myCmd = opener.DialogWin.cmd;
var myDate = new Date(); //date object for formatting MM/DD/YY
//var myCmd = 'change';
var myExceptionName = '';
var FILE = '';
function EditExcept_log(msg) {
  if(EditExceptDebug) {
    msglog(msg);
  }
}
function EditExcept_log(msg) {
  if(EditExceptDebug) {
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

function EditExcept_start(){
  EditExcept_log("EditExcept_start(), at top");

  //initialize fields on this page
  initEditException();

  //create iframe for editing 
  IFRAMENAME = "editFrame";
  if(document.getElementById(IFRAMENAME) == null) { //if iframe doesn't exist
    var iFrameHolder = document.getElementById("schedFrameHolder");
    var childFrame = document.createElement("iframe");
    childFrame.setAttribute("id",IFRAMENAME);
    childFrame.setAttribute("name",IFRAMENAME);
    childFrame.setAttribute("title","content");
    childFrame.src = '/webapi/emptypage.html';
    childFrame.width = '120';
    childFrame.height = '290';
    childFrame.scrolling = 'auto';
    iFrameHolder.appendChild(childFrame);
  }
  window.setTimeout("EditExcept_startPhase2();",0); //fixes IE appendChild() race
}

function EditExcept_startPhase2() {
  EditExcept_log("EditExcept_startPhase2(), at top");
  //EditExcept_msg('Loading "'+  FILE + '"...');
  //load iframe with target file
  var browserIE = new RegExp('internet explorer','gi');
  if(browserIE.test(navigator.appName)) {
    //Internet Explorer
    document.getElementById(IFRAMENAME).src = document.getElementById("schedFrameHolder").getAttribute("editFile");
    waitForIFrameToLoad();
  }
  else {
    //Netscape Navigator
    document.getElementById(IFRAMENAME).onload = EditExcept_startPhase3;
    //document.getElementById(IFRAMENAME).src = document.getElementById("schedFrameHolder").getAttribute("editFile");
    var locstring = new String(window.location);
    var mystring = locstring.slice(0,locstring.lastIndexOf('/') + 1) + "excepttable.htm";
    document.getElementById(IFRAMENAME).src = mystring;
  }
}

function waitForIFrameToLoad() {
  //EditExcept_log("waitForIFrameToLoad(), at top");
  var iFrameDoc = document.getElementById(IFRAMENAME).contentWindow.document;
  if(iFrameDoc.readyState == "complete") {
    EditExcept_startPhase3();
  }
  else {
    window.setTimeout("waitForIFrameToLoad()",1);
  }
}

function EditExcept_startPhase3() {
  EditExcept_log("EditExcept_startPhase3(), at top");
  //save global reference to iframe
  IFRAME = document.getElementById(IFRAMENAME);
 }

EditExcept_startPhase4.retryCount = 0;
function EditExcept_startPhase4() {
  EditExcept_log("EditExcept_startPhase4(), at top");
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
}

function initEditException() {
  //get field references
  var nstartmonth = document.getElementById('startmonth');
  var nstartday = document.getElementById('startday');
  var nstartyear = document.getElementById('startyear');
  var nendmonth = document.getElementById('endmonth');
  var nendday = document.getElementById('endday');
  var nendyear = document.getElementById('endyear');

  //initialize calendars
  fillYears('startcalendar');
  fillYears('endcalendar');
  populateTable('startcalendar');
  populateTable('endcalendar');

  //fill in fields
  if(myCmd == 'change') {
    document.title = "Change Exception";
    var infoElem = opener.GetElement(opener.DialogWin.elem,'div','info');
    //exception name
    myExceptionName = infoElem.getAttribute('exceptname');
    document.getElementById('exceptionname').value = myExceptionName;
    document.getElementById('exceptionname').readOnly = true; //disable input to exception name field
    //start date
    var startDateVal = infoElem.getAttribute('startdate');
    var myStartDateWords = startDateVal.split("/");
    nstartmonth.value = myStartDateWords[0];
    nstartday.value = myStartDateWords[1];
    //nstartyear.value = myStartDateWords[2]; //FIXTHIS: convert from 2char to 4char date
    //var myNewYear = parseInt(myStartDateWords[1],10) % 100;
    var myNewYear = parseInt(myStartDateWords[2],10) % 100;
    myNewYear = myNewYear + 2000;
    nstartyear.value = myNewYear.toString();
    //end date & type
    var endDateVal = infoElem.getAttribute('enddate');
    if(endDateVal != '') {
      var myEndDateWords = endDateVal.split("/");
      nendmonth.value = myEndDateWords[0];
      nendday.value = myEndDateWords[1];
      //nendyear.value = myEndDateWords[2]; //FIXTHIS: convert from 2char to 4char date
      //var myNewYear = parseInt(myEndDateWords[1],10) % 100;
      var myNewYear = parseInt(myEndDateWords[2],10) % 100;
      myNewYear = myNewYear + 2000;
      nendyear.value = myNewYear.toString();
      document.getElementById('multiday').checked = true;
    }
    else {
      document.getElementById('singleday').checked = true;
      hideEndDate();
    }
    setTimeout('focusElementById("startmonth")',250);
  }
  else { //cmd == add
    document.title = "Add Exception";
    //set start fields to today's date
    var today = new Date();
    nstartmonth.value = today.getMonth() + 1;
    nstartday.value = today.getDate();
    var thisYear = new String(today.getFullYear());
    //nstartyear.value = thisYear.substr(2,2);
    nstartyear.value = thisYear;
    myExceptionName = '';
    document.getElementById('exceptionname').value = '';
    document.getElementById('exceptionname').readOnly = false; //allow input to exception name field
    document.getElementById('singleday').checked = true;
    hideEndDate();
    setTimeout('focusElementById("exceptionname")',250);
  }
}

function focusElementById(id) {
  var elem = document.getElementById(id);
  elem.focus();
  elem.select();
}

function hideEndDate() {
  document.getElementById('enddate').style.visibility = 'hidden';
  if(document.getElementById('endcalendar').style.visibility == 'visible')
    document.getElementById('endcalendar').style.visibility = 'hidden';
}

function showEndDate() {
  var myEndDateElem = document.getElementById('enddate');
  if(myEndDateElem.style.visibility == 'hidden') {
    //set end date fields to match start date fields when end date becomes visible
    document.getElementById('endmonth').value = document.getElementById('startmonth').value;
    document.getElementById('endday').value = document.getElementById('startday').value;
    document.getElementById('endyear').value = document.getElementById('startyear').value;
    myEndDateElem.style.visibility = 'visible';
  }
}

function checkMonth(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  if(!isValidMonth(elem,'Month must be between 1 and 12 or "*" as wildcard, please enter month again.')) {
    setTimeout('focusElementById("' + elem.getAttribute('id') + '")',250);
    return false;
  }
  if(elem.value != '*') { //insert leading 0 if necessary
    var myVal = parseInt(elem.value,10);
    if(myVal < 10) {
      elem.value = '0' + myVal;
    }
  }
  return true;
}

function checkDay(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  if(!isValidDay(elem,'Day must be between 1 and 31 or "*" as wildcard, please enter day again.')) {
    setTimeout('focusElementById("' + elem.getAttribute('id') + '")',250);
    return false;
  }
  if(elem.value != '*') { //insert leading 0 if necessary
    var myVal = parseInt(elem.value,10);
    if(myVal < 10) {
      elem.value = '0' + myVal;
    }
  }
  return true;
}

function checkYear(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  if(!isValidYear(elem,'Year must be between 2000 and 2099 or "*" as wildcard, please enter year again.')) {
    setTimeout('focusElementById("' + elem.getAttribute('id') + '")',250);
    return false;
  }
  /*if(elem.value != '*') { //insert leading 0 if necessary
    var myVal = parseInt(elem.value,10);
    if(myVal < 10) {
      elem.value = '0' + myVal;
    }
  }*/
  return true;
}

function isValidInput() {
  if(myCmd == 'add') { //if add exception, check for exception name entered
    if(!isNotEmpty(document.getElementById('exceptionname'),'Please enter exception name.')) {
      setTimeout('focusElementById("exceptionname")',250);
      return false;
    }
  }
  //validate start date
  /*if(!isValidMonth(document.getElementById('startmonth'),'Month must be between 1 and 12 or "*" as wildcard, please enter start month again.')) {
    setTimeout('focusElementById("startmonth")',250);
    return false;
  }
  if(!isValidDay(document.getElementById('startday'),'Day must be between 1 and 31 or "*" as wildcard, please enter start day again.')) {
    setTimeout('focusElementById("startday")',250);
    return false;
  }
  if(!isValidYear(document.getElementById('startyear'),'Year must be between 0 and 99 or "*" as wildcard, please enter start year again.')) {
    setTimeout('focusElementById("startyear")',250);
    return false;
  }
  if(document.getElementById('multiday').checked == true) {
    //validate end date
  }*/
  //set return values
  opener.DialogWin.newExceptName = document.getElementById('exceptionname').value;
  opener.DialogWin.newStartDate = document.getElementById('startmonth').value + '/' +
    document.getElementById('startday').value + '/' + document.getElementById('startyear').value;
  if(document.getElementById('multiday').checked == true) {
    opener.DialogWin.newEndDate = document.getElementById('endmonth').value + '/' +
      document.getElementById('endday').value + '/' + document.getElementById('endyear').value;
  }
  else {
    opener.DialogWin.newEndDate = '';
  }
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  opener.DialogWin.newExceptSchedule = editWin.buildExceptScheduleForSave();
  return true;
}

function isNotEmpty(elem,msg) {
  var str = elem.value;
  var re = /.+/;
  if(!str.match(re)) {
    alert(msg);
    return false;
  }
  else {
    return true;
  }
}

function isValidYear(elem,msg) {
  var str = elem.value;
  //var re = /^\d{1,2}$|^\*{1}$/;
  var re = /^\d{4}$|^\*{1}$/;
  if(!str.match(re)) {
    alert(msg);
    return false;
  }
  else {
    var strVal = parseInt(str,10);
    if(!isNaN(strVal)) {
      //if(strVal < 0 || strVal > 99) {
      if(strVal < 2000 || strVal > 2099) {
        alert(msg);
        return false;
      }
    }
  }
  return true;
}

function isValidMonth(elem,msg) {
  var str = elem.value;
  var re = /^\d{1,2}$|^\*{1}$/;
  if(!str.match(re)) {
    alert(msg);
    return false;
  }
  else {
    var strVal = parseInt(str,10);
    if(!isNaN(strVal)) {
      if(strVal < 1 || strVal > 12) {
        alert(msg);
        return false;
      }
    }
  }
  return true;
}

function isValidDay(elem,msg) {
  var str = elem.value;
  var re = /^\d{1,2}$|^\*{1}$/;
  if(!str.match(re)) {
    alert(msg);
    return false;
  }
  else {
    var strVal = parseInt(str,10);
    if(!isNaN(strVal)) {
      if(strVal < 1 || strVal > 31) {
        alert(msg);
        return false;
      }
    }
  }
  return true;
}

function isValidMultiDay() {
}


function doAddException() {
  if(opener && !opener.closed && opener.DialogWin) {
    if(isValidInput()) {
      opener.DialogWin.addExceptFunc();
      window.close();
    }
  }
  else {
    alert("Application window closed.\n\nClosing editExcept window" +
      "without editExcept.");
    window.close();
  }
}

function doChangeException() {
  if(opener && !opener.closed && opener.DialogWin) {
    if(isValidInput()) {
      opener.DialogWin.changeExceptFunc();
      window.close();
    }
  }
  else {
    alert("Application window closed.\n\nClosing editDay window" +
      "without editDay.");
    window.close();
  }
}

function doOK() {
  if(myCmd == 'add') {
    doAddException();
  }
  else {
    doChangeException();
  }
}

function doRefresh() {
  EditExcept_start();
}

function doCancel() {
  window.close();
}

function doON() {
  document.getElementById('setpoint').value = 'ON';
}

function doOFF() {
  document.getElementById('setpoint').value = 'OFF';
}

function addDayCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.ExceptTableOpenAddDayDialog();
}

function deleteDayCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.ExceptTableDeleteDayCell();
}

function duplicateDayCell() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.ExceptTableDuplicateDayCell();
}

function clearDayColumn() {
  var editWin = document.getElementById(IFRAMENAME).contentWindow;
  editWin.ExceptTableClearColumn();
}

function incMonth(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startmonthup') {
    var myInputID = 'startmonth';
  }
  else {
    var myInputID = 'endmonth';
  }
  var myMonthElem = document.getElementById(myInputID);
  var myOldMonthStr = myMonthElem.value;
  if(myOldMonthStr == '*') {
    myMonthElem.value = '01';
  }
  else {
    var myNewMonth = (parseInt(myOldMonthStr,10) % 12) + 1;
    if(myNewMonth < 10) {
      myMonthElem.value = '0' + myNewMonth;
    }
    else {
      myMonthElem.value = myNewMonth.toString();
    }
  }
}

function decMonth(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startmonthdown') {
    var myInputID = 'startmonth';
  }
  else {
    var myInputID = 'endmonth';
  }
  var myMonthElem = document.getElementById(myInputID);
  var myOldMonthStr = myMonthElem.value;
  if(myOldMonthStr == '*') {
    myMonthElem.value = '12';
  }
  else {
    var myNewMonth = parseInt(myOldMonthStr,10) - 1;
    if(myNewMonth == 0)
      myNewMonth = 12;
    if(myNewMonth < 10) {
      myMonthElem.value = '0' + myNewMonth;
    }
    else {
      myMonthElem.value = myNewMonth.toString();
    }
  }
}

function incDay(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startdayup') {
    var myInputID = 'startday';
  }
  else {
    var myInputID = 'endday';
  }
  var myDayElem = document.getElementById(myInputID);
  var myOldDayStr = myDayElem.value;
  if(myOldDayStr == '*') {
    myDayElem.value = '01';
  }
  else {
    var myNewDay = (parseInt(myOldDayStr,10) % 31) + 1;
    if(myNewDay < 10) {
      myDayElem.value = '0' + myNewDay;
    }
    else {
      myDayElem.value = myNewDay.toString();
    }
  }
}

function decDay(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startdaydown') {
    var myInputID = 'startday';
  }
  else {
    var myInputID = 'endday';
  }
  var myDayElem = document.getElementById(myInputID);
  var myOldDayStr = myDayElem.value;
  if(myOldDayStr == '*') {
    myDayElem.value = '31';
  }
  else {
    var myNewDay = parseInt(myOldDayStr,10) - 1;
    if(myNewDay == 0)
      myNewDay = 31;
    if(myNewDay < 10) {
      myDayElem.value = '0' + myNewDay;
    }
    else {
      myDayElem.value = myNewDay.toString();
    }
  }
}

function incYear(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startyearup') {
    var myInputID = 'startyear';
  }
  else {
    var myInputID = 'endyear';
  }
  var myYearElem = document.getElementById(myInputID);
  var myOldYearStr = myYearElem.value;
  if(myOldYearStr == '*') {
    //use this year when changing wildcard with decrement
    var today = new Date();
    var thisYear = new String(today.getFullYear());
    //myYearElem.value = thisYear.substr(2,2);
    myYearElem.value = thisYear;
  }
  else {
    var myNewYear = (parseInt(myOldYearStr,10) + 1) % 100;
    /*if(myNewYear < 10) {
      myYearElem.value = '0' + myNewYear;
    }
    else {
      myYearElem.value = myNewYear.toString();
    }*/
    myNewYear = myNewYear + 2000;
    myYearElem.value = myNewYear.toString();
  }
}

function decYear(evt) {
  evt = (evt) ? evt : ((event) ? event : null);
  var elem = (evt.target) ? evt.target : ((evt.srcElement) ? evt.srcElement : null);
  var myElemID = elem.getAttribute('id');
  if(myElemID == 'startyeardown') {
    var myInputID = 'startyear';
  }
  else {
    var myInputID = 'endyear';
  }
  var myYearElem = document.getElementById(myInputID);
  var myOldYearStr = myYearElem.value;
  if(myOldYearStr == '*') {
    //use this year when changing wildcard with decrement
    var today = new Date();
    var thisYear = new String(today.getFullYear());
    //myYearElem.value = thisYear.substr(2,2);
    myYearElem.value = thisYear;
  }
  else {
    var myNewYear = ((parseInt(myOldYearStr,10) - 1) + 100) % 100;
    /*if(myNewYear < 10) {
      myYearElem.value = '0' + myNewYear;
    }
    else {
      myYearElem.value = myNewYear.toString();
    }*/
    myNewYear = myNewYear + 2000;
    myYearElem.value = myNewYear.toString();
  }
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

function GetName(element,t,name){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('name') &&
        elements[index].getAttribute('name') == name){ 
      e = elements[index];
      break;
    }
  }
  return e
}

function GetID(element,t,id){
  var index;
  var e = null;
  var elements = element.getElementsByTagName(t);
  for (index=0;index<elements.length;index++){
    if (elements[index].getAttribute('id') &&
        elements[index].getAttribute('id') == id){ 
      e = elements[index];
      break;
    }
  }
  return e
}

/*******************
  UTILITY FUNCTIONS
********************/
// day of week of month's first day
function getFirstDay(theYear, theMonth){
    var firstDate = new Date(theYear,theMonth,1);
    return firstDate.getDay();
}
// number of days in the month
function getMonthLen(theYear, theMonth) {
    var nextMonth = new Date(theYear, theMonth + 1, 1);
    nextMonth.setHours(nextMonth.getHours() - 3);
    return nextMonth.getDate();
}

function getElementPosition(elemID) {
	var offsetTrail = document.getElementById(elemID);
    var offsetLeft = 0;
    var offsetTop = 0;
    while (offsetTrail) {
        offsetLeft += offsetTrail.offsetLeft;
        offsetTop += offsetTrail.offsetTop;
        offsetTrail = offsetTrail.offsetParent;
    }
    if (navigator.userAgent.indexOf("Mac") != -1 && 
        typeof document.body.leftMargin != "undefined") {
        offsetLeft += document.body.leftMargin;
        offsetTop += document.body.topMargin;
    }
    return {left:offsetLeft, top:offsetTop};
}

// position and show calendar
function showCalendar(evt) {
    evt = (evt) ? evt : event;
    if (evt) {
    	var elem = (evt.target) ? evt.target : evt.srcElement;
		var calendarID = elem.getAttribute('calendarID');
    	if (document.getElementById(calendarID).style.visibility != "visible") {
            document.getElementById(calendarID).style.visibility = "visible";
        } else {
            document.getElementById(calendarID).style.visibility = "hidden";
        }
    }
}

/************************
  DRAW CALENDAR CONTENTS
*************************/
// clear and re-populate table based on form's selections
//function populateTableStart() { populateTable('startcalendar') }
//function populateTableEnd() { populateTable('endcalendar') }
function populateTable(calendarID) {
    // pick up date form choices
    var myCalendar = document.getElementById(calendarID);
    var theMonth = GetName(myCalendar,'select','chooseMonth').selectedIndex;
    var theYear = parseInt(GetName(myCalendar,'select','chooseYear').options[GetName(myCalendar,'select','chooseYear').selectedIndex].text);
    // initialize date-dependent variables
    var firstDay = getFirstDay(theYear, theMonth);
    var howMany = getMonthLen(theYear, theMonth);
    var today = new Date();
    
    // fill in month/year in table header
    var THead = GetID(myCalendar,'th','tableHeader');
    THead.innerHTML = 
        GetName(myCalendar,'select','chooseMonth').options[theMonth].text + " " + theYear;
    
    // initialize vars for table creation
    var dayCounter = 1;
    var TBody = GetID(myCalendar,'tbody','tableBody');
    // clear any existing rows
    while (TBody.rows.length > 0) {
        TBody.deleteRow(0);
    }
    var newR, newC, dateNum;
    var done=false;
    while (!done) {
        // create new row at end
        newR = TBody.insertRow(TBody.rows.length);
        if (newR) {
            for (var i = 0; i < 7; i++) {
                // create new cell at end of row
                newC = newR.insertCell(newR.cells.length);
                if (TBody.rows.length == 1 && i < firstDay) {
                    // empty boxes before first day
                    newC.innerHTML = "&nbsp;";
                    continue;
                }
                if (dayCounter == howMany) {
                    // no more rows after this one
                    done = true;
                }
                // plug in link/date (or empty for boxes after last day)
                if (dayCounter <= howMany) {
                    if (today.getFullYear() == theYear &&
                        today.getMonth() == GetName(myCalendar,'select','chooseMonth').selectedIndex &&
                        today.getDate() == dayCounter) {
                        newC.id = "today";
                    }
										if(calendarID == 'startcalendar') {
                    newC.innerHTML = "<a href='#'onclick='chooseStartDate(" + 
                        dayCounter + "," + theMonth + "," + theYear + 
                        "); return false;'>" + dayCounter + "</a>";
										}
										else {
                    newC.innerHTML = "<a href='#'onclick='chooseEndDate(" + 
                        dayCounter + "," + theMonth + "," + theYear + 
                        "); return false;'>" + dayCounter + "</a>";
										}
                     dayCounter++;
               } else {
                    newC.innerHTML = "&nbsp;";
                }
            }
        } else {
            done = true;
        }
    }
}

/*******************
  INITIALIZATIONS
********************/
// create dynamic list of year choices
//function fillYearsStart() { fillYears('startcalendar') }
//function fillYearsEnd() { fillYears('endcalendar') }
function fillYears(calendarID) {
    var today = new Date();
    var thisYear = today.getFullYear();
	var myCalendar = document.getElementById(calendarID);
    var yearChooser = GetName(myCalendar,'select','chooseYear');
    for (i = thisYear; i < thisYear + 5; i++) {
        yearChooser.options[yearChooser.options.length] = new Option(i, i);
    }
    setCurrMonth(calendarID, today);
}
// set month choice to current month
function setCurrMonth(calendarID, today) {
	var myCalendar = document.getElementById(calendarID);
    GetName(myCalendar,'select','chooseMonth').selectedIndex = today.getMonth();
}

/*******************
   PROCESS CHOICE
********************/
function chooseStartDate(date, month, year) {
  EditExcept_log("chooseStartDate(), at top");
  if(date < 10) {
    document.getElementById('startday').value = '0' + date;
  }
  else {
    document.getElementById('startday').value = date.toString();
  }
  var correctedMonth = month + 1;
  if(correctedMonth < 10) {
    document.getElementById('startmonth').value = '0' + correctedMonth;
  }
  else {
    document.getElementById('startmonth').value = correctedMonth.toString();
  }
  /*var correctedYear = year % 100;
  if(correctedYear < 10) {
    document.getElementById('startyear').value = '0' + correctedYear;
  }
  else {
    document.getElementById('startyear').value = correctedYear.toString();
  }*/
  document.getElementById('startyear').value = year.toString();
  document.getElementById('startcalendar').style.visibility = "hidden";
}

function chooseEndDate(date, month, year) {
  EditExcept_log("chooseEndDate(), at top");
  if(date < 10) {
    document.getElementById('endday').value = '0' + date;
  }
  else {
    document.getElementById('endday').value = date.toString();
  }
  var correctedMonth = month + 1;
  if(correctedMonth < 10) {
    document.getElementById('endmonth').value = '0' + correctedMonth;
  }
  else {
    document.getElementById('endmonth').value = correctedMonth.toString();
  }
  /*var correctedYear = year % 100;
  if(correctedYear < 10) {
    document.getElementById('endyear').value = '0' + correctedYear;
  }
  else {
    document.getElementById('endyear').value = correctedYear.toString();
  }*/
  document.getElementById('endyear').value = year.toString();
  document.getElementById('endcalendar').style.visibility = "hidden";
}


