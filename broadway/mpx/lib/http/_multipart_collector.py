"""
Copyright (C) 2003 2004 2010 2011 Cisco Systems

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
import cgi
import re
import string
import StringIO

from tempfile import TemporaryFile

class MultipartCollector:
    def __init__(self,request):
        request_header = request.get_headers()
        if isinstance(request_header, dict):
            hdrs = request_header
        else:
            hdrs = {}
            for h in request_header:
                splt = h.split(':')
                k = string.lower(splt[0])
                v = string.join(splt[1:],':')
                hdrs[k] = v
        # check for the right content-type
        if hdrs.has_key('content-type') and re.search(
            'multipart/form-data',hdrs['content-type']
            ):
            # check to make sure there is length, because if not it will hang on
            # reading of the data (get_data.seek(0)
            if hdrs.has_key('content-length') and int(
                hdrs['content-length']
                ) > 0:
                request.get_data().seek(0)
                f = StringIO.StringIO(request.get_data().read_all(timeout=None))
                f.seek(0)
                envirn = {'REQUEST_METHOD':'POST'}
                self.form = cgi.FieldStorage(f,headers=hdrs,environ=envirn)
        else:
            self.form = {}
    def __getitem__(self,k):
        return self.form[k]
    def has_key(self,k):
        return self.form
    def __setitem__(self,k,v):
        self.form[k] = v
    def keys(self):
        return self.form.keys()
    def __len__(self):
        return len(self.form)

class MultipartLargeFileCollector:
    """
    Specialized version of MultipartCollector that saves the data in an unnamed
    temporary file rather than a StringIO instance. It also uses a "destructive"
    read of the data-stream so that data is not needlessly collecting in the
    _DataStream StringIO object.

    This allows for much faster and memory efficient POSTs of large files.
    """
    def __init__(self,request):
        request_header = request.get_headers()
        if isinstance(request_header, dict):
            hdrs = request_header
        else:
            hdrs = {}
            for h in request_header:
                splt = h.split(':')
                k = string.lower(splt[0])
                v = string.join(splt[1:],':')
                hdrs[k] = v
        # check for the right content-type
        if hdrs.has_key('content-type') and re.search(
            'multipart/form-data',hdrs['content-type']
            ):
            # check to make sure there is length, because if not it will hang on
            # reading of the data (get_data.seek(0)
            if hdrs.has_key('content-length') and int(
                hdrs['content-length']
                ) > 0:
                f = TemporaryFile() # no name, will unlink on close()
                try:
                    data_stream = request.get_data()
                    data_stream.seek(0)
                    next_chunk = data_stream.destructive_read()
                    n_bytes = 0
                    while next_chunk:
                        f.write(next_chunk)
                        n_bytes += len(next_chunk)
                        next_chunk = data_stream.destructive_read()
                    f.seek(0)
                    envirn = {'REQUEST_METHOD':'POST'}
                    self.form = cgi.FieldStorage(f,headers=hdrs,environ=envirn)
                except:
                    f.close() # The unnamed file will unlink automatically
                    raise
        else:
            self.form = {}
    def __getitem__(self,k):
        return self.form[k]
    def has_key(self,k):
        return self.form
    def __setitem__(self,k,v):
        self.form[k] = v
    def keys(self):
        return self.form.keys()
    def __len__(self):
        return len(self.form)
