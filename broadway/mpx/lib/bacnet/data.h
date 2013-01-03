/*
Copyright (C) 2002 2010 2011 Cisco Systems

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
#include "_data.h"

extern UINT64 (*data_decode_unsigned_integer)(const unsigned char *buffer,
					      int len);
extern UINT64 (*data_decode_enumerated)(const unsigned char *buffer,
					int len);
extern INT64 (*data_decode_signed_integer)(const unsigned char *buffer,
					   int len);
extern float (*data_decode_real)(const char *buffer, int len);
extern double (*data_decode_double)(const char *buffer, int len);
// _decode_octet_string is not used outside of data.c at the moment.
extern struct OctetString (*data_decode_octet_string)(const char *buffer,
						      int len);
extern PyObject *(*data_decode_character_string)(const char *buffer, int len);
extern PyObject *(*data_decode_bit_string)(const char *buffer, int len);
extern PyObject *(*data_decode_time)(const unsigned char *buffer, int len);
extern PyObject *(*data_decode_date)(const unsigned char *buffer, int len);
extern PyObject *(*data_decode_bacnet_object_identifier)
     (const unsigned char *buffer, int len);

extern int (*data_encode_unsigned_integer)(char *buffer, int len, UINT64 value);
extern int (*data_encode_signed_integer)(char *buffer, int len, INT64 value);
extern int (*data_encode_real)(char *buffer, int len, float value);
extern int (*data_encode_double)(const char *buffer, int len, double value);

extern PyObject *(*data_encoded_date)(PyObject *this);
extern PyObject *(*data_encoded_time)(PyObject *this);
extern PyObject *(*data_encoded_bacnet_object_identifier)(PyObject *this);

// Data, Time and BACnetObjectIdentifier type pointers.
extern PyTypeObject *data_DateType;
extern PyTypeObject *data_TimeType;
extern PyTypeObject *data_BACnetObjectIdentifierType;

// CharacterString and BitString class pointer.
extern PyObject **data_CharacterString;
extern PyObject **data_BitString;

extern int load_data_references(void);
