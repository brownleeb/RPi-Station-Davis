#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""

import signal
import sys
import string
import select

from types import IntType, StringType

import fcntl
FCNTL = fcntl

import termios
TERMIOS = termios 

from log import *

from common import *



class UnixPort:
	def __init__(self, path, cfg):
		self.path = path
		self.cfg = cfg
		self._fd = None

	def open(self):
		self._fd = os.open(self.path, os.O_RDWR)
		#self.modem = corodevice.coroutine_device(self._fd)
		return self._fd

	def open_noblock(self):
		self._fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
		return self._fd

	def close(self):
		if self._fd is not None:
			self.flush()
			os.close(self._fd)
			self._fd = None

	def write(self, data, timed=1):
		if timed == 1: timeout = self.cfg['timeOutMs']/1000.
		else:          timeout = 0

		r, w, x = select.select([], [self._fd], [self._fd], 
														timeout)
		if len(r) == 0 and len(w) ==0 and len(x) == 0:
			raise TimeoutError, "Unable to write to port: '%s'" % self.path

		
		n = os.write(self._fd, data)

##    warn('write', len(data), n, repr(data))

		return n

	def _read(self, n=0):
		data = os.read(self._fd, n)
		return data

	def flush(self):
		termios.tcflush(self._fd, TERMIOS.TCIOFLUSH)

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
				raise TimeoutError, "Timeout: Unable to read from port: '%s'" % self.path

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
 
	def _findSerialPort(self, portnum):
		serialport = "/dev/ttyS%d" % portnum
		
		if os.path.exists(serialport):  return serialport

		serialport = "/dev/cua%d" % portnum

		if os.path.exists(serialport):  return serialport

		raise SerialError, "cannot get find serial port %s" % portnum



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

			if type(serialport) == IntType:
				serialport = self._findSerialPort(serialport)

			self.path = serialport
			base, fn = os.path.split(serialport)
			self._serialport = fn

			

			if not os.path.exists(self.path):
				raise SerialError, "Cannot get find serial port '%s'" % self.path
			

			flag = self._makelockfile()
			if not flag: 
				raise SerialError, "Cannot get lock on serial port '%s'.  Please "

			try:
				self._setportmode(cfg)
			except os.error, (ecode, reason):
				if ecode == 13:
					raise SerialError, "Cannot open serial port because you don't have permission to open it.  Please change the permissions using 'chmod a+rw %s'." % self.path

			self.port = UnixPort(self.path, cfg)

			if cfg['nonblock'] == 1:
				self.port.open_noblock()
			else:
				self.port.open()

			self._rsp = ''
			self._flushed = ''

	def flush(self):
			"""Save any pending input in _flushed; clear xmit/rec bufs."""
			self._trace('flush')
			self._flushed = ''

			self.port.flush()

			
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

				self._restoreportmode()
				self._removelockfile()
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

## ----------------------------------------------------------------------
## private serial methods
## ----------------------------------------------------------------------

	def _getlockpid(self):
		path = '/var/lock/LCK..%s' % self._serialport

		try:
			pid = string.strip(open(path).read())
			pid = int(pid)
		except ValueError:
			pid = 0
		except IOError:
			pid = 0

		return pid
	 

	def _makelockfile(self):
		if 1:
			pid = self._getlockpid()
			if pid == os.getpid(): return 1

			path = '/var/lock/LCK..%s' % self._serialport

			flag = 0
			while flag==0:
				try:
					fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
					flag = 1
				except os.error, (ecode, reason):
					if not os.path.exists(path):
						raise SerialError, "something is very wrong %s, %s '%s'" % (ecode, reason, path)
					if ecode == 13:
						raise SerialError, "Cannot lock serial port because you don't have permission to lock it.  Please change the permissions using 'chmod a+rw %s'." % path

					pid = self._getlockpid()

					if pid:
						if pid == os.getpid(): return 1
						try: 
							os.kill(pid, 0)
							raise SerialError, "Unable to lock the serial port '%s'.  Process %s is using the port." % (self.path, pid)
						except os.error, reason:
							os.unlink(path)
					else:
						os.unlink(path)

			os.write(fd, "%s" % os.getpid())
			os.close(fd)
		return 1

	def _removelockfile(self):
		if 1:
			path = '/var/lock/LCK..%s' % self._serialport
			pid = self._getlockpid()
			if pid == os.getpid(): 
				os.unlink(path)
 
	def _getportmode(self):
		cfg = PortDict()
		cfg['port'] = self.cfg['port']
		
		fd = os.open(self.path, os.O_RDWR)
		ret = termios.tcgetattr(fd)
		os.close(fd)

		if ret[4] == TERMIOS.B110: cfg['baud'] = Baud110
		elif ret[4] == TERMIOS.B300: cfg['baud'] = Baud300
		elif ret[4] == TERMIOS.B600: cfg['baud'] = Baud600
		elif ret[4] == TERMIOS.B1200: cfg['baud'] = Baud1200
		elif ret[4] == TERMIOS.B2400: cfg['baud'] = Baud2400
		elif ret[4] == TERMIOS.B4800: cfg['baud'] = Baud4800
		elif ret[4] == TERMIOS.B9600: cfg['baud'] = Baud9600
		elif ret[4] == TERMIOS.B19200: cfg['baud'] = Baud19200
		elif ret[4] == TERMIOS.B38400: cfg['baud'] = Baud38400
		elif ret[4] == TERMIOS.B57600: cfg['baud'] = Baud57600
		elif ret[4] == TERMIOS.B115200: cfg['baud'] = Baud115200

		if ret[2] & TERMIOS.CSTOPB: cfg['stopBits'] = TwoStopBits
		else: cfg['stopBits'] = OneStopBit

		size = ret[2] & TERMIOS.CSIZE
		if size == TERMIOS.CS5: cfg['dataBits'] = WordLength5
		elif size == TERMIOS.CS6: cfg['dataBits'] = WordLength6
		elif size == TERMIOS.CS7: cfg['dataBits'] = WordLength7
		elif size == TERMIOS.CS8: cfg['dataBits'] = WordLength8

		if ret[2] & TERMIOS.PARODD: cfg['parity'] = OddParity
		else: cfg['parity'] = EvenParity

		return cfg


	def _setportmode2(self, cfg):
		flag = self._makelockfile()
		if not flag: 
			log("cannot get lock on modem")
			return
		
		self._saved_portmode = None

		c = []

		if cfg['stopBits'] == OneStopBit:
			c.append("-cstopb")
		elif cfg['stopBits'] == TwoStopBit:
			c.append("cstopb")

		if cfg['dataBits'] == WordLength5:
			c.append("cs5")
		elif cfg['dataBits'] == WordLength6:
			c.append("cs6")
		elif cfg['dataBits'] == WordLength7:
			c.append("cs7")
		elif cfg['dataBits'] == WordLength8:
			c.append("cs8")


		if cfg['parity'] == NoParity:
			c.append("-parenb")
		if cfg['parity'] == OddParity:
			c.append("parenb")
			c.append("parodd")
		if cfg['parity'] == EvenParity:
			c.append("parenb")
			c.append("-parodd")
		if cfg['parity'] == MarkParity:
			c.append("parenb")
			c.append("parmrk")
		if cfg['parity'] == SpaceParity:
			c.append("parenb")
			c.append("-parmrk")


		cmd = "stty %s %s < %s" % (string.join(c), cfg['baud'], self.path)
		os.system(cmd)




	def _setportmode(self, cfg):
		flag = self._makelockfile()
		if not flag: 
			raise SerialError, "cannot get lock on modem"
		
		fd = os.open(self.path, os.O_RDWR)

		self._saved_portmode = termios.tcgetattr(fd)

		ret = termios.tcgetattr(fd)

		ret[0] = TERMIOS.IGNBRK | TERMIOS.IGNPAR
		ret[1] = 0
		ret[2] = TERMIOS.HUPCL | TERMIOS.CLOCAL | TERMIOS.CRTSCTS | TERMIOS.CREAD 
		
		if cfg['mode'] == Mode_Flow:
			ret[2] = ret[2] | (TERMIOS.CRTSCTS | TERMIOS.IXON | TERMIOS.IXOFF)
		elif cfg['mode'] == Mode_Raw:
			ret[2] = ret[2] & ~(TERMIOS.CRTSCTS | TERMIOS.IXON | TERMIOS.IXOFF)

		if cfg['stopBits'] == OneStopBit:
			ret[2] = ret[2] & (~TERMIOS.CSTOPB)
		elif cfg['stopBits'] == TwoStopBits:
			ret[2] = ret[2] | TERMIOS.CSTOPB

		if cfg['dataBits'] == WordLength5:
			ret[2] = ret[2] | TERMIOS.CS5
		elif cfg['dataBits'] == WordLength6:
			ret[2] = ret[2] | TERMIOS.CS6
		elif cfg['dataBits'] == WordLength7:
			ret[2] = ret[2] | TERMIOS.CS7
		elif cfg['dataBits'] == WordLength8:
			ret[2] = ret[2] | TERMIOS.CS8


		if cfg['parity'] == NoParity:
			ret[2] = ret[2] & ~TERMIOS.PARENB
		if cfg['parity'] == OddParity:
			ret[2] = ret[2] | TERMIOS.PARENB
			ret[2] = ret[2] | TERMIOS.PARODD
		if cfg['parity'] == EvenParity:
			ret[2] = ret[2] | TERMIOS.PARENB
			ret[2] = ret[2] & ~TERMIOS.PARODD 
		if cfg['parity'] == MarkParity:
			raise UnimplementedError
		if cfg['parity'] == SpaceParity:
			raise UnimplementedError

		ret[3] = 0

		ret[4] = self._setbaud(ret[4], cfg['baud'])
		ret[5] = self._setbaud(ret[5], cfg['baud'])

		r = termios.tcsetattr(fd, TERMIOS.TCSANOW, ret)
		os.close(fd)

		if 0:
			print self._getportmode()

	def _setbaud(self, ret, baud):
		if baud == 0: ret =  TERMIOS.B0
		elif baud == 50: ret =  TERMIOS.B50
		elif baud == 75: ret =  TERMIOS.B75
		elif baud == 110: ret =  TERMIOS.B110
		elif baud == 134: ret =  TERMIOS.B134
		elif baud == 150: ret =  TERMIOS.B150
		elif baud == 200: ret =  TERMIOS.B200
		elif baud == 300: ret =  TERMIOS.B300
		elif baud == 600: ret =  TERMIOS.B600
		elif baud == 1200: ret =  TERMIOS.B1200
		elif baud == 1800: ret =  TERMIOS.B1800
		elif baud == 2400: ret =  TERMIOS.B2400
		elif baud == 4800: ret =  TERMIOS.B4800
		elif baud == 9600: ret =  TERMIOS.B9600
		elif baud == 19200: ret =  TERMIOS.B19200
		elif baud == 38400: ret =  TERMIOS.B38400
		elif baud == 57600: ret =  TERMIOS.B57600
		elif baud == 115200: ret =  TERMIOS.B115200
		elif baud == 230400: ret =  TERMIOS.B230400
		elif baud == 460800: ret =  TERMIOS.B460800
		else: ret =  TERMIOS.B38400
		return ret


	def _restoreportmode(self):
		if self._saved_portmode:
			flag = self._makelockfile()
			if not flag: 
				raise SerialError, "Cannot get lock on serial port"

			fd = os.open(self.path, os.O_RDWR | os.O_NONBLOCK)
			termios.tcsetattr(fd, TERMIOS.TCSANOW, self._saved_portmode)




class UnixFilePort:
	def __init__(self, path):
		self.path = path
		self.fp = None

	def open(self):
		self.fp = open(self.path, "r")
		return self.fp

	def close(self):
		if self.fp is not None:
			fp.close()
			self.fp = None

	def write(self, data, timed=1):
		return len(data)

	def _read(self, n=0):
		if n==0: n = 1
		data = self.fp.read(n)
		if not data: raise IOError
		return data

	def flush(self):
		pass

	def read(self, cnt=0, timed=0):
		if cnt == None: return self._read(cnt)

		buffer = []
		toread = cnt

		while toread > 0:
			data = self._read(toread)
			if not data: break

			toread = toread - len(data)
			buffer.append(data)

		retdata = string.join(buffer, '')
		return retdata

	def fileno(self):
		return self.fp.fileno()

class FilePort(Port):
	def __init__(self, fn):
		self.port = PORT_CLOSED
		self.fn = fn
		self.debug = 0

	def _trace(self, tag, msg=''):
		pass
	
	def open(self, cfg):
		self.port = UnixFilePort(self.fn)
		self.port.open()

	def read(self, cnt=0, timed=0):
		return self.port.read(cnt)


