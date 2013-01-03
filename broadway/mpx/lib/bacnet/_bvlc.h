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
// BVLC-Type
#define BVLL_FOR_BACNET_IP			((unsigned char)0x81)

// BVLC-Functions
#define RESULT					((unsigned char)0x00)
#define WRITE_BROADCAST_DISTRIBUTION_TABLE	((unsigned char)0x01)
#define READ_BROADCAST_DISTRIBUTION_TABLE	((unsigned char)0x02)
#define READ_BROADCAST_DISTRIBUTION_TABLE_ACK	((unsigned char)0x03)
#define FORWARDED_NPDU				((unsigned char)0x04)
#define REGISTER_FOREIGN_DEVICE			((unsigned char)0x05)
#define READ_FOREIGN_DEVICE_TABLE		((unsigned char)0x06)
#define READ_FOREIGN_DEVICE_TABLE_ACK		((unsigned char)0x07)
#define DELETE_FOREIGN_DEVICE_TABLE_ENTRY	((unsigned char)0x08)
#define DISTRIBUTE_BROADCAST_TO_NETWORK		((unsigned char)0x09)
#define ORIGINAL_UNICAST_NPDU	 		((unsigned char)0x0A)
#define ORIGINAL_BROADCAST_NPDU 		((unsigned char)0x0B)

// J.2 BACnet Virtual Link Layer (135a J.2, page 2)
//     Paragraph 2:  Common Function Control header.
struct BVLC_HEADER {
  unsigned char type;
  unsigned char function;
  unsigned short length;
};

// J.2.1.1 BVLC-Result: Format
struct BVLC_RESULT {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'00' BVLC-Result
  unsigned short length;  // Length, in octets, of the BVLL message
  unsigned short code;	  // see BVLC Result Codes below.
};

// BVLC Result Codes
// NOTE: The definitions are adjusted for network byte order.
#define SUCCESSFUL_COMPLETION 			htons(0x0000)
#define WRITE_BROADCAST_DISTRIBUTION_TABLE_NAK 	htons(0x0010)
#define READ_BROADCAST_DISTRIBUTION_TABLE_NAK 	htons(0x0020)
#define REGISTER_FOREIGN_DEVICE_NAK 		htons(0x0030)
#define READ_FOREIGN_DEVICE_TABLE_NAK 		htons(0x0040)
#define DELETE_FOREIGN_DEVICE_TABLE_ENTRY_NAK 	htons(0x0050)
#define DISTRIBUTE_BROADCAST_TO_NETWORK_NAK 	htons(0x0060)

// J.2.2.1 BDT entry
struct BDT_ENTRY {
  unsigned char bbmd_address[6];
  unsigned long broadcast_distribution_mask;
};

// J.2.2.1 Write-Broadcast-Distribution-Table: Format
struct BVLC_WRITE_BROADCAST_DISTRIBUTION_TABLE {
  unsigned char type;	           // X'81' BVLL for BACnet/IP
  unsigned char function;          // X'01' Write-Broadcast-Distribution-Table
  unsigned short length;           // Length, in octets, of the BVLL message
  struct BDT_ENTRY bdt_entries[0]; // List of BDT Entries: N*10-octets
};

// J.2.3.1 Read-Broadcast-Distribution-Table: Format
struct BVLC_READ_BROADCAST_DISTRIBUTION_TABLE {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'02' Read-Broadcast-Distribution-Table
  unsigned short length;  // X'0004' Length, in octets, of the BVLL message
};

// J.2.4.1 Read-Broadcast-Distribution-Table-Ack: Format
struct BVLC_READ_BROADCAST_DISTRIBUTION_TABLE_ACK {
  unsigned char type;	           // X'81' BVLL for BACnet/IP
  unsigned char function;          // X'03' Read-Broadcast-Distribution-
				   // Table-Ack
  unsigned short length;           // Length, in octets, of the BVLL message
  struct BDT_ENTRY bdt_entries[0]; // List of BDT Entries: N*10-octets
};

// J.2.5.1 Forwarded-NPDU: Format
struct BVLC_FORWARDED_NPDU {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'04' Forwarded-NPDU
  unsigned short length;  // Length, in octets, of the BVLL message
  unsigned char source[6];// B/IP Address of Originating Device:  6-octets
  unsigned char npdu[0];  // Variable length
};

// J.2.6.1 Register-Foreign-Device: Format
struct BVLC_REGISTER_FOREIGN_DEVICE {
  unsigned char type;	       // X'81' BVLL for BACnet/IP
  unsigned char function;      // X'05' Register-Foreign-Device
  unsigned short length;       // Length, in octets, of the BVLL message
  unsigned short time_to_live; // Time-to-Live T, in seconds
};

// J.2.7.1 Read-Foreign-Device-Table: Format
struct BVLC_READ_FOREIGN_DEVICE_TABLE {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'06' Read-Foreign-Device-Table
  unsigned short length;  // X'0004' Length, in octets, of the BVLL message
};

// J.2.8.1 FDT entry
struct FDT_ENTRY {
  unsigned char address[6];		  // B/IP address of registrant.
  unsigned short registered_time_to_live; // Time-to-live at time of 
                                          // registration.
  unsigned short remaining_time_to_live;  // Remaining time-to-live
};

// J.2.8.1 Read-Foreign-Device-Table-Ack: Format
struct BVLC_READ_FOREIGN_DEVICE_TABLE_ACK {
  unsigned char type;	           // X'81' BVLL for BACnet/IP
  unsigned char function;          // X'07' Read-Foreign-Device-Table-Ack
  unsigned short length;           // Length, in octets, of the BVLL message
  struct FDT_ENTRY fdt_entries[0]; // List of FDT Entries: N*10-octets
};

// J.2.9.1 Delete-Foreign-Device-Table-Entry: Format
struct BVLC_DELETE_FOREIGN_DEVICE_TABLE_ENTRY {
  unsigned char type;	    // X'81' BVLL for BACnet/IP
  unsigned char function;   // X'08' Delete-Foreign-Device-Table-Entry
  unsigned short length;    // X'000A' Length, in octets, of the BVLL message
  unsigned char address[6]; // B/IP address of the table entry to delete. 
};

// J.2.10.1 Distribute-Broadcast-To-Network: Format
struct BVLC_DISTRIBUTE_BROADCAST_TO_NETWORK {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'09' Distribute-Broadcast-To-Network
  unsigned short length;  // Length, in octets, of the BVLL message
  unsigned char npdu[0];  // Variable length
};

// J.2.11.1 Original-Unicast-NPDU: Format
struct BVLC_ORIGINAL_UNICAST_NPDU {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'0A' Original-Unicast-NPDU
  unsigned short length;  // Length, in octets, of the BVLL message
  unsigned char npdu[0];  // Variable length
};

// J.2.12.1 Original-Broadcast-NPDU: Format
struct BVLC_ORIGINAL_BROADCAST_NPDU {
  unsigned char type;	  // X'81' BVLL for BACnet/IP
  unsigned char function; // X'0B' Original-Broadcast-NPDU
  unsigned short length;  // Length, in octets, of the BVLL message
  unsigned char npdu[0];  // Variable length
};

union BVLC_FUNCTION {
  struct BVLC_HEADER header;
  struct BVLC_FORWARDED_NPDU forwarded_npdu;
  struct BVLC_ORIGINAL_UNICAST_NPDU original_unicast_npdu ;
  struct BVLC_ORIGINAL_BROADCAST_NPDU original_broadcast_npdu;
};

struct BMAC_ADDR { // @fixme  Use this?
  unsigned long addr;
  unsigned short port;
};
