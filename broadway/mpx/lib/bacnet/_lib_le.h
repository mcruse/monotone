/*
Copyright (C) 2010 2011 Cisco Systems

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
#ifndef INT16
#define INT16 __int16_t
#endif

#ifndef UINT16
#define UINT16 __uint16_t
#endif

#ifndef INT32
#define INT32 __int32_t
#endif

#ifndef UINT32
#define UINT32 __uint32_t
#endif

#ifndef INT64
#define INT64 __int64_t
#endif

#ifndef UINT64
#define UINT64 __uint64_t
#endif

// Network Layer Protocol Control Information.
// See ANSI/ASHAE 135-1995 section 6.2.2.
struct PACKED_NPCI {
  unsigned char version;	// * Version octet.
				// * Control octet.
  unsigned char priority : 2;	//   Bits 1,0.
				//   Bit 2.
  unsigned char data_expecting_reply : 1;
  unsigned char sspec : 1;	//   Bit 3.
  unsigned char reserved2 : 1;	//   Bit 4:  Must be 0.
  unsigned char dspec : 1;	//   Bit 5.
  unsigned char reserved1 : 1;	//   Bit 6:  Must be 0.
  unsigned char network_msg : 1;//   Bit 7.

  unsigned char data[0];	// * Variable octets.
  // dnet			   2 optional octets.
  // dlen			   1 optional octet.
  // dadr			dlen optional octets.
  // snet			   2 optional octets.
  // slen			   1 optional octet.
  // sadr			slen optional octets.
  // hop_count			   1 optional octet.
  // msg_type			   2 optional octets.
  // vendor_id			   1 optional octet.
} __attribute__ ((packed));


//
// ANSI/ASHAE 135-1995 section 20.1.2 (page 323-325)
// BACnet-Confirmed-Request-PDU (segmented-message=0)
//
struct CONFIRMED_REQUEST_PDU {
					// ** Byte 0
  unsigned char reserved1 : 1;		// Bit 0:    0
					// Bit 1:
  unsigned char segmented_response_accepted : 1;
  unsigned char more_follows : 1;	// Bit 2:
  unsigned char segmented_message : 1;	// Bit 3:    0
  unsigned char pdu_type : 4;		// Bits 4-7: CONFIRMED_REQUEST_TYPE (0)
					// ** Byte 1
					// Bits 0-3:
  unsigned char max_apdu_length_accepted : 4;
  unsigned char reserved2 : 4;		// Bits 4-7: 0
  unsigned char invoke_id;		// ** Byte 2
  unsigned char service_choice;		// ** Byte 3
  unsigned char service_request[0];	// ** Encoded bytes 4-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.2 (page 323-325)
// BACnet-Confirmed-Request-PDU (segmented-message=1)
//
struct SEGMENTED_CONFIRMED_REQUEST_PDU {
					// ** Byte 0
  unsigned char reserved : 1;		// Bit 0:    0
					// Bit 1
  unsigned char segmented_response_accepted : 1;
  unsigned char more_follows : 1;	// Bit 2
  unsigned char segmented_message : 1;	// Bit 3:    1
  unsigned char pdu_type : 4;		// Bits 4-7: CONFIRMED_REQUEST_TYPE (0)
					// ** Byte 1
					// Bits 0-3:
  unsigned char max_apdu_length_accepted : 4;
  unsigned char reserved2 : 4;		// Bits 4-7: 0
  unsigned char invoke_id;		// ** Byte 2
  unsigned char sequence_number;	// ** Byte 3
  unsigned char proposed_window_size;	// ** Byte 4
  unsigned char service_choice;		// ** Byte 5
  unsigned char service_request[0];	// ** Encoded bytes 6-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.3 (page 325-326)
// BACnet-Unconfirmed-Request-PDU
//
struct UNCONFIRMED_REQUEST_PDU {
					// ** Byte 0
  unsigned char reserved : 4;		// Bits 0-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7:UNCONFIRMED_REQUEST_TYPE(1)
  unsigned char service_choice;		// ** Byte 1
  unsigned char service_request[0];	// ** Encoded bytes 2-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.4 (page 326-327)
// BACnet-SimpleACK-PDU
//
struct SIMPLE_ACK_PDU {
					// ** Byte 0
  unsigned char reserved : 4;		// Bits 0-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7: SIMPLE_ACK_TYPE (2)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char service_ack_choice;	// ** Byte 2
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.5 (page 327-329)
// BACnet-ComplexACK-PDU (segmented-message=1)
//
struct SEGMENTED_COMPLEX_ACK_PDU {
					// ** Byte 0
  unsigned char reserved : 2;		// Bits 0-1: 0
  unsigned char more_follows : 1;	// Bit 2
  unsigned char segmented_message : 1;	// Bit 3:    1
  unsigned char pdu_type : 4;		// Bits 4-7: COMPLEX_ACK_TYPE (3)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char sequence_number;	// ** Byte 2
  unsigned char proposed_window_size;	// ** Byte 3
  unsigned char service_ack_choice;	// ** Byte 4
  unsigned char service_ack[0];		// ** Encoded bytes 5-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.5 (page 327-329)
// BACnet-ComplexACK-PDU (segmented-message=0)
//
struct COMPLEX_ACK_PDU {
					// ** Byte 0
  unsigned char reserved : 2;		// Bits 0-1: 0
  unsigned char more_follows : 1;	// Bit 2     
  unsigned char segmented_message : 1;	// Bit 3:    0
  unsigned char pdu_type : 4;		// Bits 4-7: COMPLEX_ACK_TYPE (3)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char service_ack_choice;	// ** Byte 2
  unsigned char service_ack[0];		// ** Encoded bytes 3-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.6 (page 329-331)
// BACnet-SegmentACK-PDU
//
struct SEGMENT_ACK_PDU {
					// ** Byte 0
  unsigned char server : 1;		// Bit 0:
  unsigned char negative_ack : 1;	// Bit 1
  unsigned char reserved : 2;		// Bits 2-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7: SEGMENT_ACK_TYPE (4)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char sequence_number;	// ** Byte 2
  unsigned char actual_window_size;	// ** Byte 3
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.7 (page 331-332)
// BACnet-Error-PDU
//
struct ERROR_PDU {
					// ** Byte 0
  unsigned char reserved : 4;		// Bits 0-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7: ERROR_TYPE (5)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char error_choice;		// ** Byte 2
  unsigned char error[0];		// ** Encoded bytes 3-*
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.8 (page 332-333)
// BACnet-Reject-PDU
//
struct REJECT_PDU {
					// ** Byte 0
  unsigned char reserved : 4;		// Bits 0-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7: REJECT_TYPE (6)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char reject_reason;		// ** Byte 2
} __attribute__ ((packed));

//
// ANSI/ASHAE 135-1995 section 20.1.9 (page 333-334)
// BACnet-Abort-PDU
//
struct ABORT_PDU {
					// ** Byte 0
  unsigned char server   : 1;		// Bit 0: SRV
  unsigned char reserved : 3;		// Bits 1-3: 0
  unsigned char pdu_type : 4;		// Bits 4-7: ABORT_TYPE (7)
  unsigned char invoke_id;		// ** Byte 1
  unsigned char abort_reason;		// ** Byte 2
} __attribute__ ((packed));

//
// Used to determine the actual PDU structure to use.
//
struct UNKNOWN_PDU {
  unsigned char reserved : 2;		// bits 0-1
  unsigned char more_follows : 1;	// bit 2
  unsigned char segmented_message : 1;	// bit 3
  unsigned char pdu_type : 4;		// bits 4-7
} __attribute__ ((packed));

union PACKED_APCI {
  unsigned char *p_start;
  struct UNKNOWN_PDU *unknown;
  struct CONFIRMED_REQUEST_PDU *confirmed_request;
  struct SEGMENTED_CONFIRMED_REQUEST_PDU *segmented_confirmed_request;
  struct UNCONFIRMED_REQUEST_PDU *unconfirmed_request;
  struct SIMPLE_ACK_PDU *simple_ack;
  struct SEGMENTED_COMPLEX_ACK_PDU *segmented_complex_ack;
  struct COMPLEX_ACK_PDU *complex_ack;
  struct SEGMENT_ACK_PDU *segment_ack;
  struct ERROR_PDU *error;
  struct REJECT_PDU *reject;
  struct ABORT_PDU *abort;
};

//
// ANSI/ASHAE 135-1995 section 20.2.1 (page 335-347)
//
struct BACNET_TAG {
  union {					// Bits 0-2
    unsigned char length : 3;
    unsigned char value : 3;
    unsigned char type : 3;
  } u;
  unsigned char class : 1;			// Bit 3
  unsigned char tag_number : 4;			// Bits 4-7
} __attribute__ ((packed));

struct  BACNET_NPCI_OFFSET {
  int valid;
  int dnet;
  int dlen;
  int dadr;
  int snet;
  int slen;
  int sadr;
  int hop_count;
  int msg_type;
  int vendor_id;
  int apci;
  int data;
};

// Network Layer Protocol Control Information.
// See ANSI/ASHAE 135-1995 section 6.2.2.
struct BACNET_NPCI {
  unsigned char version;	// * Version octet.
				// * Control octet.
  unsigned char priority : 2;	//   Bits 1,0.
				//   Bit 2.
  unsigned char data_expecting_reply : 1;
  unsigned char sspec : 1;	//   Bit 3.
  unsigned char reserved2 : 1;	//   Bit 4:  Must be 0.
  unsigned char dspec : 1;	//   Bit 5.
  unsigned char reserved1 : 1;	//   Bit 6:  Must be 0.
  unsigned char network_msg : 1;//   Bit 7.
  unsigned short dnet;		//    2 optional octets.
  unsigned char dlen;		//    1 optional octet.
  unsigned char dadr[31];	// dlen optional octets.
  unsigned short snet;		//    2 optional octets.
  unsigned char slen;		//    1 optional octet.
  unsigned char sadr[31];	// slen optional octets.
  unsigned char hop_count;	//    1 optional octet.
  unsigned char msg_type;	//    1 optional octet.
  unsigned short vendor_id;	//    2 optional octets.
} __attribute__ ((packed));

enum PDU_TYPE {
  CONFIRMED_REQUEST_TYPE = 0,
  UNCONFIRMED_REQUEST_TYPE = 1,
  SIMPLE_ACK_TYPE = 2,
  COMPLEX_ACK_TYPE = 3,
  SEGMENT_ACK_TYPE = 4,
  ERROR_TYPE = 5,
  REJECT_TYPE = 6,
  ABORT_TYPE = 7
};

// Application Protocol Data Unit (HEADER).
// See ANSI/ASHAE 135-1995 section ?.
struct BACNET_APCI {
  // The order of these bit-fields is optimized for copying to and from the
  // the real APCI structures.
  unsigned char server : 1;			// bit 0
  unsigned char segmented_response_accepted : 1;// bit 1
  unsigned char more_follows : 1;		// bit 2
  unsigned char segmented_message : 1;		// bit 3
  unsigned char pdu_type : 4;			// bits 4-7
  unsigned char max_apdu_length_accepted : 4;	// bits 0-3
  unsigned char negative_ack : 1;		// bit 4 (oh well)
  unsigned char reserved_bits : 2;
  unsigned char invalid_apci : 1;		// bit 7
  unsigned char invoke_id;
  unsigned char reason;
  unsigned char sequence_number;
  unsigned char window_size;
  unsigned char choice;
  unsigned char reserved_byte;			// Make struct 8 bytes...
} __attribute__ ((packed));

enum NET_PRIORITY {
  normal = 0,
  urgent = 1,
  critical_equipment = 2,
  life_safety = 3
};

struct ADDR {
  unsigned char length;
  unsigned char address[31];
};

struct SOCKET_MAP {
  int direct;
  int broadcast;
  int limited_broadcast; // Limited broadcast (255.255.255.255) socket
  int network;           // This socket's network.
  struct ADDR interface_address;
  struct ADDR broadcast_address;
};

enum NET_MSG_TYPE {
  WHO_IS_ROUTER = 0X00,
  I_AM_ROUTER = 0X01,
  I_COULD_BE_ROUTER = 0X02,
  REJECT_MESSAGE = 0X03,
  ROUTER_BUSY = 0X04,
  ROUTER_AVAILABLE = 0X05,
  INIT_ROUTING_TABLE = 0X06,
  INIT_ROUTING_TABLE_ACK = 0X07,
  ESTABLISH_CONNECTION = 0X08,
  DISCONNECT_CONNECTION = 0X09,
  NONE = 0x00
};

struct BACNET_BUFFER {
  int size;			// The *total* size of the allocated BACnet
				// buffer, including *all* meta data.
  int allocated:1;
  int valid:1;
  struct BACNET_NPCI_OFFSET npci_offset;
  void *p_mac;			// Optional MAC data.
  void *p_llc;			// Optional LLC data.
  struct PACKED_NPCI *p_npci;	// Variable length NPCI.
  union PACKED_APCI apci;	// Optional, variable, APCI header.
  void *p_data;			// Points to NPDU/APDU data.
  int   s_data;
  unsigned char pad[128];	// Used for the:
				//   (Optional) MAC/LLC/etc... data, the
				//   variable length BACNET_NPCI and optional,
				//   variable length, APCI header.
  unsigned char _data[0];	// Network Message or APDU data.
};

