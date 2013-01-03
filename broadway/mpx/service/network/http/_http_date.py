"""
Copyright (C) 2002 2009 2010 2011 Cisco Systems

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
"""
import time
from mpx.lib import msglog
# From draft-ietf-http-v11-spec-07.txt/3.3.1
#       Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
#       Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
#       Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
def _unpack_rfc822(data):
	format = '%a, %d %b %Y %H:%M:%S gmt'
	return time.strptime(data,format)
def _unpack_rfc850(data):
	format = '%A, %d-%b-%y %H:%M:%S gmt'
	return time.strptime(data,format)
def _unpack_asctime(data):
	format = '%a %b %d %H:%M:%S %Y'
	return time.strptime(data,format)
def parse_http_date(data):
	data = data.lower().strip()
	try:
		if data[3] == ',':
			timestamp = time.mktime(_unpack_rfc822(data))
			return timestamp - _calc_offset(timestamp)
		elif ',' in data:
			timestamp = time.mktime(_unpack_rfc850(data))
			return timestamp - _calc_offset(timestamp)
		else:
			return time.mktime(_unpack_asctime(data)[0:-1] + (-1,))
	except ValueError:
		msglog.exception('Bad time format encountered: %s' % data)
	return 0
def _calc_offset(timestamp):
	# is DST supported, and was the timestamp in DST.
	if time.daylight and time.localtime(timestamp)[-1]:
		return time.altzone
	else:
		return time.timezone
def build_http_date (when):
	return time.strftime ('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(when))
