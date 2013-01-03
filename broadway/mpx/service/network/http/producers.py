"""
Copyright (C) 2002 2003 2010 2011 Cisco Systems

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
import string

class StreamingProducer:
	def __init__(self, stream, buffer_size=1024):
		self._stream = stream
		self._buffer_size = buffer_size
	def more(self):
		return self._stream.read(self._buffer_size)
class SimpleProducer:
	"producer for a string"
	def __init__(self, data, buffer_size=1024):
		self.data = data
		self.buffer_size = buffer_size
	def more(self):
		if len(self.data) > self.buffer_size:
			result = self.data[:self.buffer_size]
			self.data = self.data[self.buffer_size:]
			return result
		else:
			result = self.data
			self.data = ''
			return result
class ScanningProducer:
	"like simple_producer, but more efficient for large strings"
	def __init__(self, data, buffer_size=1024):
		self.data = data
		self.buffer_size = buffer_size
		self.pos = 0
	def more(self):
		if self.pos < len(self.data):
			lp = self.pos
			rp = min(
				len(self.data),
				self.pos + self.buffer_size
				)
			result = self.data[lp:rp]
			self.pos = self.pos + len(result)
			return result
		else:
			return ''
class LinesProducer:
	"producer for a list of lines"
	def __init__(self, lines):
		self.lines = lines
	def ready(self):
		return len(self.lines)
	def more(self):
		if self.lines:
			chunk = self.lines[:50]
			self.lines = self.lines[50:]
			return string.join(chunk, '\r\n') + '\r\n'
		else:
			return ''
class BufferListProducer:
	"producer for a list of buffers"
	def __init__(self, buffers):
		self.index = 0
		self.buffers = buffers
	def more(self):
		if self.index >= len(self.buffers):
			return ''
		else:
			data = self.buffers[self.index]
			self.index = self.index + 1
			return data
class FileProducer:
	"producer wrapper for file[-like] objects"
	out_buffer_size = 1<<16
	def __init__(self, file):
		self.done = 0
		self.file = file
	def more(self):
		if self.done:
			return ''
		else:
			data = self.file.read(self.out_buffer_size)
			if not data:
				self.file.close()
				del self.file
				self.done = 1
				return ''
			else:
				return data

class OutputProducer:
	"Acts like an output file; suitable for capturing sys.stdout"
	def __init__(self):
		self.data = ''	
	def write(self, data):
		lines = string.splitfields(data, '\n')
		data = string.join(lines, '\r\n')
		self.data = self.data + data
	def writeline(self, line):
		self.data = self.data + line + '\r\n'
	def writelines(self, lines):
		self.data = self.data + string.joinfields(lines,'\r\n') + '\r\n'
	def ready(self):
		return (len(self.data) > 0)
	def flush(self):
		pass
	def softspace(self, *args):
		pass
	def more(self):
		if self.data:
			result = self.data[:512]
			self.data = self.data[512:]
			return result
		else:
			return ''
class CompositeProducer:
	"combine a fifo of producers into one"
	def __init__(self, producers):
		self.producers = producers
	def more(self):
		while len(self.producers):
			p = self.producers.first()
			d = p.more()
			if d:
				return d
			else:
				self.producers.pop()
		else:
			return ''
class GlobbingProducer:
	"""
	'glob' the output from a producer into a particular buffer size.
	helps reduce the number of calls to send().  [this appears to
	gain about 30% performance on requests to a single channel]
	"""
	def __init__(self, producer, buffer_size=1<<16):
		self.producer = producer
		self.buffer = ''
		self.buffer_size = buffer_size
	def more(self):
		while len(self.buffer) < self.buffer_size:
			data = self.producer.more()
			if data:
				self.buffer = self.buffer + data
			else:
				break
		r = self.buffer
		self.buffer = ''
		return r
class HookedProducer:
	"""
	A producer that will call <function> when it empties,.
	with an argument of the number of bytes produced.  Useful
	for logging/instrumentation purposes.
	"""
	debug = False
	def __init__(self, producer, function, debug=None):
		if debug is not None:
			self.debug = debug
		self.producer = producer
		self.function = function
		self.bytes = 0
		self.results = []
	def more(self):
		if self.producer:
			result = self.producer.more()
			if not result:
				self.producer = None
				if self.debug:
					extrainfo = "".join(self.results)
				else:
					extrainfo = ""
				self.function(self.bytes, extrainfo)
				self.function = None
				self.results = []
			else:
				self.bytes = self.bytes + len(result)
			if self.debug:
				self.results.append(result)
			return result
		else:
			return ''

# HTTP 1.1 emphasizes that an advertised Content-Length header MUST be
# correct.  In the face of Strange Files, it is conceivable that
# reading a 'file' may produce an amount of data not matching that
# reported by os.stat() [text/binary mode issues, perhaps the file is
# being appended to, etc..]  This makes the chunked encoding a True
# Blessing, and it really ought to be used even with normal files.
# How beautifully it blends with the concept of the producer.

class ChunkedProducer:
	def __init__(self, producer, footers=None):
		self.producer = producer
		self.footers = footers
	def more(self):
		if self.producer:
			data = self.producer.more()
			if data:
				return '%x\r\n%s\r\n' % (len(data), data)
			else:
				self.producer = None
				if self.footers:
					return string.join(
						['0'] + self.footers,
						'\r\n'
						) + '\r\n\r\n'
				else:
					return '0\r\n\r\n'
		else:
			return ''
# Unfortunately this isn't very useful right now (Aug 97), because
# apparently the browsers don't do on-the-fly decompression.  Which
# is sad, because this could _really_ speed things up, especially for
# low-bandwidth clients (i.e., most everyone).
try:
	import zlib
except ImportError:
	zlib = None
class CompressedProducer:
	"""
	Compress another producer on-the-fly, using ZLIB
	[Unfortunately, none of the current browsers seem to support this]
	"""
	# Note: It's not very efficient to have the server repeatedly
	# compressing your outgoing files: compress them ahead of time, or
	# use a compress-once-and-store scheme.  However, if you have low
	# bandwidth and low traffic, this may make more sense than
	# maintaining your source files compressed.
	#
	# Can also be used for compressing dynamically-produced output.
	def __init__(self, producer, level=5):
		self.producer = producer
		self.compressor = zlib.compressobj(level)
	def more(self):
		if self.producer:
			cdata = ''
			# feed until we get some output
			while not cdata:
				data = self.producer.more()
				if not data:
					self.producer = None
					return self.compressor.flush()
				else:
					cdata = self.compressor.compress(data)
			return cdata
		else:
			return ''
class EscapingProducer:
	"A producer that escapes a sequence of characters"
	" Common usage: escaping the CRLF.CRLF sequence in SMTP, NNTP, etc..."
	def __init__(self, producer, esc_from='\r\n.', esc_to='\r\n..'):
		self.producer = producer
		self.esc_from = esc_from
		self.esc_to = esc_to
		self.buffer = ''
		from asynchat import find_prefix_at_end
		self.find_prefix_at_end = find_prefix_at_end
	def more(self):
		esc_from = self.esc_from
		esc_to   = self.esc_to
		buffer = self.buffer + self.producer.more()
		if buffer:
			buffer = string.replace(buffer, esc_from, esc_to)
			i = self.find_prefix_at_end(buffer, esc_from)
			if i:
				# we found a prefix
				self.buffer = buffer[-i:]
				return buffer[:-i]
			else:
				# no prefix, return it all
				self.buffer = ''
				return buffer
		else:
			return buffer
