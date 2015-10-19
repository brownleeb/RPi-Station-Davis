#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""


import sys
import string
import select

from types import IntType, StringType

from log import *

from common import *

class TcpPort:
	def __init__(self, iphost, ipport, cfg):
		self.iphost = iphost
		self.ipport = ipport

		self.cfg = cfg
		self._fd = None

	def open(self):
		self.port = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.port.connect((self.iphost, int(self.ipport)))

		self._fd = self.port.fileno()

		return self._fd

	def open_noblock(self):
		return self.open()

	def close(self):
		if self._fd is not None:
			self.flush()

			self.port.close()
			self.port = None
			self._fd = None

	def write(self, data, timed=1):
		if timed == 1: timeout = self.cfg['timeOutMs']/1000.
		else:          timeout = 0

		r, w, x = select.select([], [self._fd], [self._fd], 
														timeout)
		if len(r) == 0 and len(w) ==0 and len(x) == 0:
			raise TimeoutError, "Unable to write to port: '%s'" % self.path

		n = self.port.send(data)

##		warn('write', len(data), n, repr(data))

		return n

	def _read(self, n=0):
		data = self.port.recv(n)
		return data

	def flush(self):
##		termios.tcflush(self._fd, TERMIOS.TCIOFLUSH)
		pass

	def read(self, cnt=0, timed=0):
		if cnt == None: return self._read(cnt)

		buffer = []
		toread = cnt

		if timed == 1: timeout = self.cfg['timeOutMs']/1000.
		else:          timeout = 0

		while toread > 0:
			r, w, x = select.select([self._fd], [], [self._fd], 
															timeout)

			if len(r) == 0 and len(w) ==0 and len(x) == 0:
				raise TimeoutError, "Timeout: Unable to read from port: '%s:%s'" % (self.iphost, self.ipport)

			if len(r) > 0:
				data = self._read(toread)
				if not data: break

				toread = toread - len(data)
				buffer.append(data)

		retdata = string.join(buffer, '')
		return retdata

	def fileno(self):
		return self._fd


class Port:

	"""Encapsulate methods for accessing the Win32 serial ports.

		Public methods:
			 open(cfg) -- Open port specified by PortDict instance cfg.

			 flush()  -- Empty receive and transmit buffers.

			 getLastFlush() -- Return the last string that was flushed.

			 getLastRsp()  -- Return the last response.

			 close() -- Close the connection.

			 write(str, cnt=None) -- Write cnt (len(str), if cnt=None) 
			 bytes of str to port.

			 writeVerifyEcho(str, cnt=None) -- sSame as write, but verify 
			 each chr was echoed.

			 read(cnt=None, timed=FALSE) -- Try to return cnt bytes read from port
			 (cnt==None, read whatever is there, cnt!=None & timed==TRUE, then read 
			 must complete in configured timeOutMs time).

			 readTerminated() -- Read from port until terminator string read.
			 Must complete within timeOutMs, return string minus the terminator.

			 cmd(str='') -- Write or writeVerifyEcho str, then read till rspType
			 satisfied, or times out.

"""

	def __init__(self):
			"""Instance created, but not attached to any port."""
			self.debug = FALSE
			self.port = PORT_CLOSED
			self.cfg = {}
			self._rsp = ''
			self._bufSize = 0
			self._flushed = ''
			self.path = None
			self._serialport = None

	def _trace(self, tag, msg=''):
			"""If debugging enabled, print a message"""
			if self.debug:
					warn('Port.%s: %s' % (tag, msg))
 

	def open(self, cfg):
			"""Attach to the port specified in the cfg arg, then:

			-Open the port, set baud, parity, stopBits, and dataBits as per cfg.
			-Clear xmit/rec buffers, enable DTR, RTS, disable flow ctl.

			"""
			self.debug = cfg['debug']
			self._trace('open')
			if self.port != PORT_CLOSED:
				raise SerialError, 'Port is already open'

			self.cfg = cfg

			serialport = cfg['port']

			if type(serialport) != StringType:
				raise SerialError, "invalid tcp port %s" % serialport

			self.path = serialport
			parts = string.split(serialport, ":", 1)
			iphost = parts[0]
			ipport = parts[1]
			if not ipport: ipport = 23

			self.port = TcpPort(iphost, ipport, cfg)

			self.port.open()

			self._rsp = ''
			self._flushed = ''

	def flush(self):
			"""Save any pending input in _flushed; clear xmit/rec bufs."""
			self._trace('flush')
			self._flushed = ''

##			self.port.flush()

			
	def getLastFlush(self):
			"""Return the last contents of the flushed buffer."""
			return self._flushed[:]

	def getLastRsp(self):
			"""Return the last contents of the response buffer."""
			return self._rsp[:]

	def close(self):
			"""Close the port."""
			self._trace('close')

			if self.port:
				self.port.close()

				self.port = PORT_CLOSED

	def write(self, str, cnt=None):
			"""Write cnt bytes of str out port, cnt defaults to len(str)."""
			self._trace('write')
			n = self.port.write(str)
			return n


	def writeVerifyEcho(self, str, cnt=None):
			"""Same as write , but verify each char was echoed by the hdw. """
			self._trace('writeVerifyEcho')
			raise UnimplementedError

	def read(self, cnt=None, timed=FALSE):
			"""Attempt to read cnt bytes, if timed TRUE, must complete in cfg time.
			"""
			return self.port.read(cnt, timed)

	def readTerminated(self, term):
			"""Read from port until terminator read, timed out, or buf overflow.
			Terminator is stripped off of result."""

			if len(term) != 1: 
				raise IOError, "readTerminated's terminator has to have one character in the pattern"

			buffer = []

			while 1:
				c = self.port.read(1, timed=1)

				if c == term: break
				buffer.append(c)

			return string.join(buffer, '')

	def readTerminated2(self, term):
			"""Read from port until terminator read, timed out, or buf overflow.
			Terminator is stripped off of result."""

			if len(term) != 2: 
				raise IOError, "readTerminated2's terminator has to have two characters in the pattern"

			buffer = []
			termlength = term
			termbuff = ''

			while 1:
				c = self.port.read(1, timed=1)

				if len(buffer) >= 2 and c == term[1] and buffer[-1] == term[0]: break

				buffer.append(c)

			return string.join(buffer, '')

	def cmd(self, str=''):
			"""Send a str, get a rsp according to cfg."""

			self.flush()
			n = self.port.write(str + self.cfg['rspTerm'])

			line = self.readTerminated(self.cfg['cmdTerm'])

			return line

	def fileno(self):
		return self.port.fileno()


