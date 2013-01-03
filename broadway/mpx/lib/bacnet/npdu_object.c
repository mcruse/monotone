/*
Copyright (C) 2001 2002 2004 2010 2011 Cisco Systems

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
////
// @todo Rewrite as a real class.

#include <Python.h>
#include <structmember.h>

#include "lib.h"
#include "npdu_object.h"

long n_NPDU_instances = 0;

static struct memberlist npdu_memberlist[];
static struct PyMethodDef npdu_methodlist[];

// Allocate a new object and zap our bit (BACNET_NPDU) with zeros
// The ":NPDU" argument to PyArg_ParseTuple() is used in the
// error string if there is a problem. Less the ':' that is.

char __doc__NPDU[] = "\n"
"##\n"
"# MontyDoc string for NPDU.\n"
"#";
PyObject *
new_npdu(PyObject *self, PyObject *args)
{
  npdu_object *o;

  if (!PyArg_ParseTuple(args, ":NPDU"))
    return NULL;

  o = PyObject_New(npdu_object, &npdu_type);
  if (o) {
    memset(&o->npci, 0, sizeof(o->npci));
    memset(&o->apci, 0, sizeof(o->apci));
    memset(&o->data, 0, sizeof(o->data));
    o->datalen = 0;
  }
  n_NPDU_instances += 1;
  return (PyObject *)o;
}

static void
npdu_dealloc(PyObject *self)
{
  n_NPDU_instances -= 1;
  PyObject_Del(self); // Accounted for (in dealloc).
}

// Get an NPCI attribute value. Things that can be done automatically
// do not appear here and are described in the npdu_memberlist[] array.
// They only include simple types for now. Strings will work in 2.1.1.
// Bitfields will need some more magic from the Python guys.

static PyObject *
npdu_getattr(PyObject *this, char *name)
{
  static int initialized = 0;
  static PyObject *members = NULL;
  npdu_object *self = (npdu_object *)this;
  PyObject *result = NULL;
  if (!initialized) {
    members = Py_BuildValue("(sssssssssssssssssssssssssssss)",
			    "choice",
			    "dadr",
			    "data",
			    "data_expecting_reply",
			    "dlen",
			    "dnet",
			    "dspec",
			    "hop_count",
			    "invalid_apdu",
			    "invoke_id",
			    "max_apdu_length_accepted",
			    "more_follows",
			    "msg_type",
			    "negative_ack",
			    "network_msg",
			    "priority",
			    "pdu_type",
			    "reason",
			    "sadr",
			    "segmented_message",
			    "segmented_response_accepted",
			    "sequence_number",
			    "server",
			    "slen",
			    "snet",
			    "sspec",
			    "vendor_id",
			    "version",
			    "window_size"
			    );
    initialized = 1;
  }
  if (strcmp(name, "__members__") == 0) {
    Py_INCREF(members);	// Increment to indicate that this module references
			// this object too.
    return members;
  }
  // "choice"
  if (strcmp(name, "dadr") == 0)
    return Py_BuildValue("s#", self->npci.dadr, self->npci.dlen);
  if (strcmp(name, "data") == 0)
    return Py_BuildValue("s#", self->data, self->datalen);
  if (strcmp(name, "data_expecting_reply") == 0)
    return Py_BuildValue("i", self->npci.data_expecting_reply);
  // "dlen"
  // "dnet"
  if (strcmp(name, "dspec") == 0)
    return Py_BuildValue("i", self->npci.dspec);
  // "hop_count"
  if (strcmp(name, "invalid_apdu") == 0)
    return Py_BuildValue("i", self->apci.invalid_apci);
  // "invoke_id"
  if (strcmp(name, "max_apdu_length_accepted") == 0)
    return Py_BuildValue("i", self->apci.max_apdu_length_accepted);
  if (strcmp(name, "more_follows") == 0)
    return Py_BuildValue("i", self->apci.more_follows);
  // "msg_type"
  if (strcmp(name, "negative_ack") == 0)
    return Py_BuildValue("i", self->apci.negative_ack);
  if (strcmp(name, "network_msg") == 0)
    return Py_BuildValue("i", self->npci.network_msg);
  if (strcmp(name, "priority") == 0)
    return Py_BuildValue("i", self->npci.priority);
  if (strcmp(name, "pdu_type") == 0)
    return Py_BuildValue("i", self->apci.pdu_type);
  // "reason"
  if (strcmp(name, "sadr") == 0)
    return Py_BuildValue("s#", self->npci.sadr, self->npci.slen);
  if (strcmp(name, "segmented_message") == 0)
    return Py_BuildValue("i", self->apci.segmented_message);
  if (strcmp(name, "segmented_response_accepted") == 0)
    return Py_BuildValue("i", self->apci.segmented_response_accepted);
  // "server flag (true if from server)"
  if (strcmp(name, "server") == 0)
    return Py_BuildValue("i", self->apci.server);
  // "slen"
  // "snet"
  if (strcmp(name, "sspec") == 0)
    return Py_BuildValue("i", self->npci.sspec);
  // "vendor_id"
  // "version",
  // "window_size"

  result = Py_FindMethod(npdu_methodlist, (PyObject *)self, name);
  if (result != NULL)
    return result;
  PyErr_Clear();	// Clear the AttributeError set by Py_FindMethod.  If
			// it is not clear, it will be incorrectly rasied
			// later.

  return PyMember_Get((char *)self, npdu_memberlist, name);
}

// This is the complement of npci_getattr() and all the comments for
// that function apply here as well. The only non-symmetry is due to
// the validation code necessary variable sized arguments like strings.
// Some range checking may be useful for integer and bitfields in the
// future.

static int
npdu_setattr(PyObject *this, char *name, PyObject *o)
{
  npdu_object *self = (npdu_object *)this;

  // "choice"
  if (strcmp(name, "dadr") == 0) {
    if (PyString_Size(o) <= sizeof(self->npci.dadr)) {
      memcpy(self->npci.dadr, PyString_AsString(o), PyString_Size(o));
      self->npci.dlen = PyString_Size(o);
      return 0;
    } else {
      broadway_raise("EOverflow",
                     PyString_FromString("Destination address too long."), NULL);
      return -1;
    }
  }
  if (strcmp(name, "data") == 0) {
    if (PyString_Size(o) < sizeof(self->data)) {
      memcpy(self->data, PyString_AsString(o), PyString_Size(o));
      self->datalen = PyString_Size(o);
      return 0;
    } else {
      broadway_raise("EOverflow", PyString_FromString("Too much data."), NULL);
      return -1;
    }
  }
  if (strcmp(name, "data_expecting_reply") == 0) {
    self->npci.data_expecting_reply = PyInt_AsLong(o);
    return 0;
  }
  // "dlen"
  // "dnet"
  if (strcmp(name, "dspec") == 0) {
    self->npci.dspec = PyInt_AsLong(o);
    return 0;
  }
  // "hop_count"
  if (strcmp(name, "invalid_apdu") == 0) {
    self->apci.invalid_apci = PyInt_AsLong(o);
    return 0;
  }
  // "invoke_id"
  if (strcmp(name, "max_apdu_length_accepted") == 0) {
    self->apci.max_apdu_length_accepted = PyInt_AsLong(o);
    return 0;
  }
  if (strcmp(name, "more_follows") == 0) {
    self->apci.more_follows = PyInt_AsLong(o);
    return 0;
  }
  // "msg_type"
  if (strcmp(name, "negative_ack") == 0) {
    self->apci.negative_ack = PyInt_AsLong(o);
    return 0;
  }
  if (strcmp(name, "network_msg") == 0) {
    self->npci.network_msg = PyInt_AsLong(o);
    return 0;
  }
  if (strcmp(name, "priority") == 0) {
    self->npci.priority = PyInt_AsLong(o);
    return 0;
  }
  if (strcmp(name, "pdu_type") == 0) {
    self->apci.pdu_type = PyInt_AsLong(o);
    return 0;
  }
  // "reason"
   if (strcmp(name, "sadr") == 0) {
     if (PyString_Size(o) <= sizeof(self->npci.sadr)) {
       memcpy(self->npci.sadr, PyString_AsString(o), PyString_Size(o));
       self->npci.slen = PyString_Size(o);
       return 0;
     } else {
       broadway_raise("EOverflow",
                      PyString_FromString("source address too long."), NULL);
       return -1;
     }
   }
  if (strcmp(name, "segmented_message") == 0) {
    self->apci.segmented_message = PyInt_AsLong(o);
    return 0;
  }
  if (strcmp(name, "segmented_response_accepted") == 0) {
    self->apci.segmented_response_accepted = PyInt_AsLong(o);
    return 0;
  }
  // "sequence_number"
  if (strcmp(name, "server") == 0) {
    self->apci.server = PyInt_AsLong(o);
    return 0;
  }
  // "slen"
  // "snet"
  if (strcmp(name, "sspec") == 0) {
    self->npci.sspec = PyInt_AsLong(o);
    return 0;
  }
  // "vendor_id"
  // "version"
  // "window_size"
  return PyMember_Set((char *)self, npdu_memberlist, name, o);
}

static PyObject *fromstring(PyObject *this, PyObject *args)
{
  struct BACNET_BUFFER *buffer;
  char *data;
  int length;
  void *pdata;
  PyObject *string;
  npdu_object *self = (npdu_object *)this;

  if (!PyArg_ParseTuple(args, "O", &string)) {
    return NULL;
  }
  if (!PyString_Check(string)) {
    PyErr_SetString(PyExc_TypeError, "Argument must be a string.");
    return NULL;
  }
  // Allocate a BACnet buffer large enough to decode the string.
  length = PyString_Size(string);
  buffer = bacnet_alloc_buffer(length);
  if (!buffer) {
    return NULL;
  }

  data = PyString_AsString(string);

  // Construct the buffer as if it had just "read" in a BACnet message.
  buffer->p_mac = buffer->_data;
  buffer->p_llc = buffer->_data;
  buffer->p_npci = (struct PACKED_NPCI*)buffer->_data;
  buffer->p_data = buffer->_data;
  buffer->s_data = length;
  memcpy(buffer->p_data, data, length);

  // Now decode the buffer.
  length = decode_existing_buffer(buffer, &self->npci, &self->apci, &pdata);
  if (length < 0) {
    bacnet_free_buffer(buffer);
    return NULL;
  }

  // Copy the extra data from the buffer to the NPDU's data attribute.
  if (length > sizeof(self->data)) {
    bacnet_free_buffer(buffer);
    // @fixme Better exception.
    broadway_raise("EOverflow", PyString_FromString("Too much data."), NULL);
    return NULL;
  }
  self->datalen = length;
  memcpy(self->data, pdata, length);

  bacnet_free_buffer(buffer);

  Py_INCREF(this);
  return this;
}

static void PyString_ConcatString(PyObject **pyTarget, char *zString)
{
  PyObject *object = PyString_FromString(zString);
  PyString_ConcatAndDel(pyTarget, object);
}

////
// Generates a Python string that is a human readable dump of the NPDU.
// @return A string.
// @todo This implementation is super ineffecient.  Use fewer string objects
//       in the construction of the final object.
// @todo Look into sharing the static tables for the rest of the implementation.
static PyObject *__str__(PyObject *this)
{
  static const char *network_priorities[] = {
    "Normal message", "Urgent message",
    "Critical Equipment message", "Life Safety message"
  };
  static const char *message_types[] = {
    "Who-Is-Router-To-Network", "I-Am-Router-To-Network",
    "I-Could-Be-Router-To-Network", "Reject-Message-To-Network",
    "Router-Busy-To-Network", "Router-Available-To-Network",
    "Initialize-Routing-Table", "Initialize-Routing-Table-Ack",
    "Establish-Connection-To-Network", "Disconnect-Connection-To-Network"
  };
  static const char *pdu_types[] = {
    "BACnet-Confirmed-Service-Request-PDU",
    "BACnet-Unconfirmed-Service-Request-PDU",
    "BACnet-SimpleACK-PDU", "BACnet-ComplexACK-PDU", "BACnet-SegmentACK-PDU",
    "BACnet-Error-PDU", "BACnet-Reject-PDU", "BACnet-Abort-PDU"
  };
  static const char *max_octets_accepted[] = {
    "50 octets", "128 octets", "206 octets", "480 octets", "1024 octets",
    "1476 octets",
    "reserved by ASHRAE", "reserved by ASHRAE", "reserved by ASHRAE",
    "reserved by ASHRAE", "reserved by ASHRAE", "reserved by ASHRAE",
    "reserved by ASHRAE", "reserved by ASHRAE", "reserved by ASHRAE",
    "reserved by ASHRAE",
  };
  static const char *bacnet_confirmed_service_choices[] = {
    "acknowledgeAlarm", "confirmedCOVNotification", "confirmedEventNotification",
    "getAlarmSummary", "getEnrollmentSummary", "subscribeCOV", "atomicReadFile",
    "atomicWriteFile", "addListElement", "removeListElement", "createObject",
    "deleteObject", "readProperty", "readPropertyConditional",
    "readPropertyMultiple", "writeProperty", "writePropertyMultiple",
    "deviceCommunicationControl", "confirmedPrivateTransfer",
    "confirmedTextMessage", "reinitializeDevice", "vtOpen", "vtClose", "vtData",
    "authenticate", "requestKey"
  };
  static const char *bacnet_unconfirmed_service_choices[] = {
    "i-Am", "i-Have", "unconfirmedCOVNotification",
    "unconfirmedEventNotification", "unconfirmedPrivateTransfer",
    "unconfirmedTextMessage", "timeSynchronization", "who-Has", "who-Is",
    "utcTimeSynchronization"
  };
  static const char *bacnet_reject_reason[] = {
    "other", "buffer-overflow", "inconsistent-parameters",
    "invalid-parameter-data-type", "invalid-tag", "missing-required-parameter",
    "parameter-out-of-range", "too-many-arguments", "undefined-enumeration",
    "unrecognized-service"
  };
  static const char *bacnet_abort_reason[] = {
    "other", "buffer-overflow", "invalid-apdu-in-this-state",
    "preempted-by-higher-priority-task", "segmentation-not-supported"
  };
  int i, n;
  char buffer[1024];
  PyObject *result = NULL;
  npdu_object *self = (npdu_object *)this;

  result = PyString_FromString("NPCI [ASHRAE 135-1995 sub-clause 6.2.2]:\n");
  sprintf(buffer, "  Version: %d (%s)\n", self->npci.version,
          (self->npci.version == 1) ? "ASHRAE 135-1995" : "Unknown");
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "  Control: 0x%2.2x\n", ((unsigned char *)&self->npci)[1]);
  PyString_ConcatString(&result, buffer);
  // Break out the control flags.
  sprintf(buffer, "    network message: %d       [bit 7]\n",
          self->npci.network_msg);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    reserved: %d              [bit 6]\n",
          self->npci.reserved1);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    destination specifier: %d [bit 5]\n", self->npci.dspec);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    reserved: %d              [bit 4]\n",
          self->npci.reserved2);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    source specifier: %d      [bit 3]\n", self->npci.sspec);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    data_expecting_reply: %d  [bit 2]\n",
          self->npci.data_expecting_reply);
  PyString_ConcatString(&result, buffer);
  sprintf(buffer, "    priority: %d              [bits 1,0] (%s)\n",
          self->npci.priority, network_priorities[self->npci.priority]);
  PyString_ConcatString(&result, buffer);
  // If there is a destination specifier then print the destination network
  // and the destination address. If the destination address length is 0
  // then this is a broadcast message so say that.
  if (self->npci.dspec) {
    sprintf(buffer, "DNET: %d (0x%4.4x)\n", self->npci.dnet, self->npci.dnet);
    PyString_ConcatString(&result, buffer);
    sprintf(buffer, "DLEN: %d (0x%2.2x)\n", self->npci.dlen, self->npci.dlen);
    PyString_ConcatString(&result, buffer);
    sprintf(buffer, "DADR: ");
    PyString_ConcatString(&result, buffer);
    if (self->npci.dlen) {
      for (i = 0; i < self->npci.dlen; i++) {
	sprintf(buffer, "%2.2x ", self->npci.dadr[i]);
        PyString_ConcatString(&result, buffer);
      }
      PyString_ConcatString(&result, "(hex)");
    } else {
      sprintf(buffer, (self->npci.dnet == 0xffff) ? "Global Broadcast" 
                                                  : "Remote Broadcast");
      PyString_ConcatString(&result, buffer);
    }
    PyString_ConcatString(&result, "\n");
  } else {
    // @todo Validate dnet, and dlen are zero.
  }
  // If there is a source specifier then print the source network and the
  // source address. A source address length of zero is illegal.
  if (self->npci.sspec) {
    sprintf(buffer, "  SNET: %d (0x%4.4x)\n", self->npci.snet, self->npci.snet);
    PyString_ConcatString(&result, buffer);
    sprintf(buffer, "  SLEN: %d (0x%2.2x) %s\n", self->npci.slen,
            self->npci.slen,
            (self->npci.slen) ? "" : "Invalid source address");
    PyString_ConcatString(&result, buffer);
    sprintf(buffer, "  SADR: ");
    PyString_ConcatString(&result, buffer);
    for (i = 0; i < self->npci.slen; i++) {
      sprintf(buffer, "%2.2x ", self->npci.sadr[i]);
      PyString_ConcatString(&result, buffer);
    }
    if (self->npci.slen) {
      PyString_ConcatString(&result, "(hex)\n");
    }
  } else {
    // @todo Validate snet, and slen are zero.
  }
  // If there was a destination specifier then there will be a hop count.
  if (self->npci.dspec) {
    sprintf(buffer, "  Hop Count: %d (0x%2.2x)\n", self->npci.hop_count,
            self->npci.hop_count);
    PyString_ConcatString(&result, buffer);
  } else {
    // @todo Validate hop_count is zero.
  }
  // If it is a network message there will be message type. Could decode
  // these further.
  if (self->npci.network_msg) {
    sprintf(buffer, "  Message Type: 0x%2.2x (%s)\n",
            self->npci.msg_type,
            (self->npci.msg_type < 10)
            ? message_types[self->npci.msg_type]
            : (self->npci.msg_type < 0x80) ? "Reserved for use by ASHRAE"
                                           : "Proprietary message");
    PyString_ConcatString(&result, buffer);
  } else {
    // @todo Validate msg_type is zero.
  }
  // If the message type is greater than 0x80 then it is a vendor proprietary
  // message.
  if (self->npci.network_msg && self->npci.msg_type >= 0x80) {
    sprintf(buffer, "  Vendor ID: %d (0x%4.4x)\n",
            self->npci.vendor_id, self->npci.vendor_id);
    PyString_ConcatString(&result, buffer);
  } else {
    // @todo Validate msg_type is zero.
  }
  // APCI dumpage
  if (!self->npci.network_msg) {
    PyString_ConcatString(&result,
                          "APCI [ASHRAE 135-1995 sub-clause 20.1]:\n");
    if (self->apci.invalid_apci) {
      sprintf(buffer, "  invalid_apdu: %d [Error:  Failed to decode the APCI]",
              self->apci.invalid_apci);
      PyString_ConcatString(&result, buffer);
    } else {
      sprintf(buffer, "  pdu-type: 0x%2.2x (%s)\n", self->apci.pdu_type,
              pdu_types[self->apci.pdu_type]);
      PyString_ConcatString(&result, buffer);

      if (self->apci.pdu_type == 0 || self->apci.pdu_type == 3) {
        sprintf(buffer, "  segmented-message: %d\n", self->apci.segmented_message);
        PyString_ConcatString(&result, buffer);
        sprintf(buffer, "  more-follows: %d\n", self->apci.more_follows);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 0) {
        sprintf(buffer, "  segmented-response-accepted: %d\n",
                self->apci.segmented_response_accepted);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 0) {
        sprintf(buffer, "  max-APDU-length-accepted: 0x%2.2x (%s)\n",
                self->apci.max_apdu_length_accepted,
                max_octets_accepted[self->apci.max_apdu_length_accepted]);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 4) {
        sprintf(buffer, "  negative-ACK: %d\n", self->apci.negative_ack);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 4 || self->apci.pdu_type == 7) {
        sprintf(buffer, "  server: %d\n", self->apci.server);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 0 || self->apci.pdu_type == 2 ||
          self->apci.pdu_type == 3) {
        sprintf(buffer, "  invokeID: 0x%2.2x\n", self->apci.invoke_id);
        PyString_ConcatString(&result, buffer);
      } else if (self->apci.pdu_type == 4 || self->apci.pdu_type == 5 ||
          self->apci.pdu_type == 6 || self->apci.pdu_type == 7) {
        sprintf(buffer, "  original-invokeID: 0x%2.2x\n",
                self->apci.invoke_id);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 0) {
        if (self->apci.segmented_message) {
          sprintf(buffer, "  sequence-number: 0x%2.2x "
                  "[ASHRAE 1995-135 sub-clause 20.1.2.6]\n",
                  self->apci.sequence_number);
          PyString_ConcatString(&result, buffer);
        }
      } else if (self->apci.pdu_type == 3) {
        if (self->apci.segmented_message) {
          sprintf(buffer, "  sequence-number: 0x%2.2x "
                  "[ASHRAE 1995-135 sub-clause 20.1.5.4]\n",
                  self->apci.sequence_number);
          PyString_ConcatString(&result, buffer);
        } else if (self->npci.data_expecting_reply) {
          sprintf(buffer, "  sequence-number: 0x%2.2x "
                  "[empirical, NOT ASHRAE 1995-135 sub-clause 20.1.5.4]\n",
                  self->apci.sequence_number);
          PyString_ConcatString(&result, buffer);
        } else {
          // @todo Some sort of validataion.
        }
      } else if (self->apci.pdu_type == 4) {
        sprintf(buffer, "  sequence-number: 0x%2.2x "
                "[ASHRAE 1995-135 sub-clause 20.1.6.4]\n",
                self->apci.sequence_number);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      if (self->apci.pdu_type == 0) {
        if (self->apci.segmented_message) {
          sprintf(buffer, "  proposed-window-size: %d "
                  "[ASHRAE 1995-135 sub-clause 20.1.2.7]\n",
                  self->apci.window_size);
          PyString_ConcatString(&result, buffer);
        } else {
          // @todo Some sort of validataion.
        }
      } else if (self->apci.pdu_type == 3) {
        if (self->apci.segmented_message) {
          sprintf(buffer, "  proposed-window-size: %d "
                  "[ASHRAE 1995-135 sub-clause 20.1.5.4]\n",
                  self->apci.window_size);
          PyString_ConcatString(&result, buffer);
        } else if (self->npci.data_expecting_reply) {
          sprintf(buffer, "  proposed-window-size: %d "
                  "[empirical, NOT ASHRAE 1995-135 sub-clause 20.1.5.4]\n",
                  self->apci.window_size);
          PyString_ConcatString(&result, buffer);
        } else {
          // @todo Some sort of validataion.
        }
      } else if (self->apci.pdu_type == 4) {
        sprintf(buffer, "  actual-window-size: %d\n", self->apci.window_size);
        PyString_ConcatString(&result, buffer);
      } else {
        // @todo Some sort of validataion.
      }
      switch (self->apci.pdu_type) {
      case 0:
        sprintf(buffer, "  service-choice: %d (%s)\n",
                self->apci.choice,
                (self->apci.choice < 26)
                ? bacnet_confirmed_service_choices[self->apci.choice]
                : "Invalid BACnetConfirmedServiceChoice");
        PyString_ConcatString(&result, buffer);
        break;
      case 1:
        sprintf(buffer, "  serivce-choice: %d (%s)\n",
                self->apci.choice,
                (self->apci.choice < 10)
                ? bacnet_unconfirmed_service_choices[self->apci.choice]
                : "Invalid BACnetUnconfirmedServiceChoice");
        PyString_ConcatString(&result, buffer);
        break;
      case 2:
      case 3:
        sprintf(buffer, "  service-ACK-choice: %d (%s)\n",
                self->apci.choice,
                (self->apci.choice < 26)
                ? bacnet_confirmed_service_choices[self->apci.choice]
                : "Invalid BACnetConfirmedServiceChoice");
        PyString_ConcatString(&result, buffer);
        break;
      case 4:
        break;
      case 5:
        sprintf(buffer, "  error-choice: %d (%s)\n",
                self->apci.choice,
                (self->apci.choice < 26)
                ? bacnet_confirmed_service_choices[self->apci.choice]
                : "Invalid BACnetConfirmedServiceChoice");
        PyString_ConcatString(&result, buffer);
        break;
      case 6:
        sprintf(buffer, "  reject-reason: %d (%s)\n",
                self->apci.reason,
                (self->apci.reason < 10)
                ? bacnet_reject_reason[self->apci.reason]
                : "Invalid BACnetRejectReason");
        PyString_ConcatString(&result, buffer);
        break;
      case 7:
        sprintf(buffer, "  abort-reason: %d (%s)\n",
                self->apci.reason,
                (self->apci.reason < 10)
                ? bacnet_abort_reason[self->apci.reason]
                : "Invalid BACnetAbortReason");
        PyString_ConcatString(&result, buffer);
        break;
      default:
        // @todo Some sort of validataion.
        break;
      }
    }
  }
  if (self->datalen) {
    if (!self->npci.network_msg) {
      PyString_ConcatString(&result, "APDU data:");
    } else {
      PyString_ConcatString(&result, "NPDU data:");
    }
  }
  for (i = 0; i < self->datalen; i++) {
    if ((i % 16) == 0) {
      PyString_ConcatString(&result, "\n  |");
      for (n = i; n < i+16; n++) {
        if (n < self->datalen && isprint(self->data[n])) {
          sprintf(buffer, "%c", self->data[n]);
          PyString_ConcatString(&result, buffer);
        } else {
          PyString_ConcatString(&result, " ");
        }
      }
      PyString_ConcatString(&result, "|  ");
    }
    sprintf(buffer, "%2.2x ", self->data[i]);
    PyString_ConcatString(&result, buffer);
  }
  return result;
}

////
// Generates a Python string that represents the data that would be
// transmitted if the NPDU were sent (via NPDU.send()).
// @return A string that contains the encoded NPDU.
// @note The generated character string is transport agnostic and
//       does not include any MAC data.
// @fixme Extract the common buffer building code into an 'encode_npdu'
//        helper function used be both this function and NPDU.send().
static PyObject *tostring(PyObject *self, PyObject *args)
{
  struct BACNET_BUFFER *buffer;
  PyObject *result = NULL;
  npdu_object *o = (npdu_object *)self;

  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  buffer = encode_new_buffer(&o->npci, &o->apci, o->data, o->datalen);
  if (!buffer) {
    return NULL;
  }
  result = PyString_FromStringAndSize((char *)buffer->p_npci,
				      (char *)buffer->p_data - 
				      (char *)buffer->p_npci +
				      buffer->s_data);
  bacnet_free_buffer(buffer);
  return result;
}

////
// Prints a summary of the NPDU to a file.
// @return 0
static int __print__(PyObject *this, FILE *fp, int flags)
{ 
  // @fixme Evil duplicate table.
  static const char *message_types[] = {
    "Who-Is-Router-To-Network", "I-Am-Router-To-Network",
    "I-Could-Be-Router-To-Network", "Reject-Message-To-Network",
    "Router-Busy-To-Network", "Router-Available-To-Network",
    "Initialize-Routing-Table", "Initialize-Routing-Table-Ack",
    "Establish-Connection-To-Network", "Disconnect-Connection-To-Network"
  };
  // @fixme Evil duplicate table.
  static const char *pdu_types[] = {
    "BACnet-Confirmed-Service-Request-PDU",
    "BACnet-Unconfirmed-Service-Request-PDU",
    "BACnet-SimpleACK-PDU", "BACnet-ComplexACK-PDU", "BACnet-SegmentACK-PDU",
    "BACnet-Error-PDU", "BACnet-Reject-PDU", "BACnet-Abort-PDU"
  };
  PyObject *str;
  npdu_object *self = (npdu_object *)this;

  if (flags & Py_PRINT_RAW) {
    str = __str__(this);
    if (str != NULL) {
      fprintf(fp, "%s", PyString_AS_STRING(str));
      Py_DECREF(str);
      return 0;
    }
  }
  if (self->npci.network_msg) {
    if (self->npci.msg_type < 10) {
      fprintf(fp, "<%s npdu>", message_types[self->npci.msg_type]);
    } else {
      fprintf(fp, "<npdu 0x%02x - %s>", self->npci.msg_type,
              (self->npci.msg_type) ? "Reserved for use by ASHRAE"
              : "Proprietary message");
    }
  } else {
    if (self->apci.invalid_apci) {
      fprintf(fp, "<invalid apdu>");
    } else {
      fprintf(fp, "<%s>", pdu_types[self->apci.pdu_type]);
    }
  }
  if (flags & Py_PRINT_RAW) {
    fprintf(fp, "\"");
  }
  return 0;
}

////
// @return A non-zero integer if self and other are equal, otherwise return 0.
static int npdu_cmp(PyObject *this, PyObject *that)
{
  int n;
  npdu_object *self = (npdu_object *)this;
  npdu_object *other = (npdu_object *)that;

  if (other->ob_type != &npdu_type) {
    PyErr_SetString(PyExc_TypeError,
		    "Can only compare an NPDU with other NPDU objects.");
    return 0;
  }
  n = memcmp(&self->npci, &other->npci, sizeof self->npci);
  if (!n) {
    n = memcmp(&self->apci, &other->apci, sizeof self->apci);
    if (!n && self->datalen != other->datalen) {
      n = (self->datalen < other->datalen) ? -1 : 1 ;
      if (!n) {
	n = memcmp(self->data, other->data, self->datalen);
      }
    }
  }
  return n;
}

// Initialise the object descriptor and hook in the supported internal methods.

PyTypeObject npdu_type = {
  PyObject_HEAD_INIT(&PyType_Type)// Standard header.
  0,
  "npdu",			// Name.
  sizeof(npdu_object),		// Basic Size.
  0,				// Item size.
  npdu_dealloc,			// tp_dealloc.
  __print__,			// tp_print.
  npdu_getattr,			// tp_getattr.
  npdu_setattr,			// tp_set_attr.
  npdu_cmp,			// tp_compare.
  0,				// tp_repr.
  0,				// tp_as_number.
  0,				// tp_as_sequence.
  0,				// tp_as_mapping.
  0,				// tp_hash.
  0,				// tp_call
  __str__,			// tp_str
  0,				// tp_getattro
  0,				// tp_setattro
};

#define OFF(x) offsetof(npdu_object, x)

static struct memberlist npdu_memberlist[] = {
  {"choice", T_UBYTE, OFF(apci.choice)},
  {"dlen", T_UBYTE, OFF(npci.dlen)},
  {"dnet", T_USHORT, OFF(npci.dnet)},
  {"hop_count", T_UBYTE, OFF(npci.hop_count)},
  {"invoke_id", T_UBYTE, OFF(apci.invoke_id)},
  {"msg_type", T_UBYTE, OFF(npci.msg_type)},
  {"reason", T_UBYTE, OFF(apci.reason)},
  {"sequence_number", T_UBYTE, OFF(apci.sequence_number)},
  {"slen", T_UBYTE, OFF(npci.slen)},
  {"snet", T_USHORT, OFF(npci.snet)},
  {"vendor_id", T_USHORT, OFF(npci.vendor_id)},
  {"version", T_UBYTE, OFF(npci.version)},
  {"window_size", T_UBYTE, OFF(apci.window_size)},
  {NULL}
};

static struct PyMethodDef npdu_methodlist[] = {
  {"tostring", tostring, METH_VARARGS},
  {"fromstring", fromstring, METH_VARARGS},
  {NULL}
};
