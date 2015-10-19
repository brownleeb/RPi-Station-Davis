"""HTTP client class -- an API compatible replacement for httplib.py
												which is much faster! - jeske@egroups.net

See the following URL for a description of the HTTP/1.0 protocol:
http://www.w3.org/hypertext/WWW/Protocols/
(I actually implemented it from a much earlier draft.)

Example:

>>> from httplib import HTTP
>>> h = HTTP('www.python.org')
>>> h.putrequest('GET', '/index.html')
>>> h.putheader('Accept', 'text/html')
>>> h.putheader('Accept', 'text/plain')
>>> h.endheaders()
>>> errcode, errmsg, headers = h.getreply()
>>> if errcode == 200:
...     f = h.getfile()
...     print f.read() # Print the raw HTML
...
<HEAD>
<TITLE>Python Language Home Page</TITLE>
[...many more lines...]
>>>

Note that an HTTP object is used for a single request -- to issue a
second request to the same server, you create a new HTTP object.
(This is in accordance with the protocol, which uses a new TCP
connection for each request.)
""" #"

import socket
import string
import mimetools
import fhttplib

ip_cache = {}

HTTP_VERSION = 'HTTP/1.0'
HTTP_PORT = 80

class HTTP:
		"""This class manages a connection to an HTTP server."""
		def __init__(self, host = '', port = 0):
				"""Initialize a new instance.

				If specified, `host' is the name of the remote host to which
				to connect.  If specified, `port' specifies the port to which
				to connect.  By default, httplib.HTTP_PORT is used.

				"""
				self.debuglevel = 0
				self.file = None
				self.send_buffer = ""
				if host: self.connect(host, port)
		
		def set_debuglevel(self, debuglevel):
				"""Set the debug output level.

				A non-false value results in debug messages for connection and
				for all messages sent to and received from the server.

				"""
				self.debuglevel = debuglevel
		
		def connect(self, host, port = 0):
				"""Connect to a host on a given port.
				
				Note:  This method is automatically invoked by __init__,
				if a host is specified during instantiation.

				"""
				if not port:
						i = string.find(host, ':')
						if i >= 0:
								host, port = host[:i], host[i+1:]
								try: port = string.atoi(port)
								except string.atoi_error:
										raise socket.error, "nonnumeric port"
				if not port: port = HTTP_PORT
				self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				if self.debuglevel > 0: print 'connect:', (host, port)
				try:
					host_ip = fhttplib.ip_cache[host]
				except KeyError:
					host_ip = socket.gethostbyname(host)
					fhttplib.ip_cache[host] = host_ip

				self.sock.connect((host_ip, port))
		
		def throttlesendbuffer(self):
			if len(self.send_buffer):
				self.sock.send(self.send_buffer)
				self.send_buffer = ""

		def send(self, str):
				"""Send `str' to the server."""
				if self.debuglevel > 0: print 'send:', `str`
				self.send_buffer = self.send_buffer + str
				# self.sock.send(str)
		
		def putrequest(self, request, selector):
				"""Send a request to the server.

				`request' specifies an HTTP request method, e.g. 'GET'.
				`selector' specifies the object being requested, e.g.
				'/index.html'.

				"""
				if not selector: selector = '/'
				str = '%s %s %s\r\n' % (request, selector, HTTP_VERSION)
				self.send(str)
		
		def putheader(self, header, *args):
				"""Send a request header line to the server.

				For example: h.putheader('Accept', 'text/html')

				"""
				str = '%s: %s\r\n' % (header, string.joinfields(args,'\r\n\t'))
				self.send(str)
		
		def endheaders(self):
				"""Indicate that the last header line has been sent to the server."""
				self.send('\r\n')
		
		def getreply(self):
				"""Get a reply from the server.
				
				Returns a tuple consisting of:
				- server response code (e.g. '200' if all goes well)
				- server response string corresponding to response code
				- any RFC822 headers in the response from the server

				"""
				self.throttlesendbuffer()
				self.file = self.sock.makefile('rb')
				line = self.file.readline()
				if self.debuglevel > 0: print 'reply:', `line`
				try:
						[ver, code, msg] = string.split(line, None, 2)
				except ValueError:
					try:
							[ver, code] = string.split(line, None, 1)
							msg = ""
					except ValueError:
							self.headers = None
							return -1, line, self.headers
				if ver[:5] != 'HTTP/':
						self.headers = None
						return -1, line, self.headers
				errcode = string.atoi(code)
				errmsg = string.strip(msg)
				self.headers = mimetools.Message(self.file, 0)
				return errcode, errmsg, self.headers
		
		def getfile(self):
				"""Get a file object from which to receive data from the HTTP server.

				NOTE:  This method must not be invoked until getreplies
				has been invoked.

				"""
				return self.file
		
		def close(self):
				"""Close the connection to the HTTP server."""
				if self.file:
						self.file.close()
				self.file = None
				if self.sock:
						self.sock.close()
				self.sock = None

import asynchat
import asyncore
try:
	asyncore.ExitNow
	asyncore.version = 2
except AttributeError:
	asyncore.version = 1

import select, errno
import cStringIO

from log import *

class async_timeout_loop:
		"""
			This encapsulates similar functionality to the asyncore code, but
			with one difference: if the timeout expires without a read/write 
			event, then the flag self.timedout is set and loop returns.
		"""
		socket_map = asyncore.socket_map
		
		def __init__ (self):
			self.timedout = 0

		def poll1 (self, timeout=0.0):
				if self.socket_map:
						map = self.socket_map
						sockets = map.keys()
						r = filter (lambda x: x.readable(), sockets)
						w = filter (lambda x: x.writable(), sockets)
						e = sockets[:]

						(r,w,e) = select.select (r,w,e, timeout)

						if not r and not w and not e:
								self.timedout = 1
								return

						for x in r:
								try:
										x.handle_read_event()
								except:
										apply(x.handle_error, sys.exc_info())

						for x in w:
								try:
										x.handle_write_event()
								except:
										apply(x.handle_error, sys.exc_info())


		def poll2 (self, timeout=0.0):
			if self.socket_map:
				map = self.socket_map
				if asyncore.version == 2:
					r = []; w = []; e = []
					for fd, obj in map.items():
						if obj.readable(): r.append (fd)
						if obj.writable(): w.append (fd)
						e.append(fd)

				(r,w,e) = select.select (r,w,e, timeout)

				if not r and not w and not e:
						self.timedout = 1
						return

				for x in r:
					obj = map[fd]
					try:
						obj.handle_read_event()
					except:
						apply(obj.handle_error, sys.exc_info())

				for x in w:
					obj = map[fd]
					try:
						obj.handle_write_event()
					except:
						apply(obj.handle_error, sys.exc_info())

		def loop (self, timeout=0.0):
			while self.socket_map:
				if asyncore.version == 1: self.poll1(timeout)  
				else: self.poll2(timeout)  
				if self.timedout: 
					return


class async_http_client (asynchat.async_chat):
		"""
			Simple async client.  This really isn't a "chat" client, as 
			it assumes a request/response/close model of HTTP/1.0 without 
			keepalive.  It just collects the data, and is then asked for
			it later.
		"""

		def __init__ (self, address):
				asynchat.async_chat.__init__ (self)

				if type (address) is type (''):
					family = socket.AF_UNIX
				else:
					family = socket.AF_INET

				self.family = family
				self.address = address

				self.set_terminator (None)
				self.buffer = []

				self.create_socket (self.family, socket.SOCK_STREAM)
				self.connect (self.address)

		def log (*ignore):
				pass

		def collect_incoming_data (self, data):
				self.buffer.append (data)

		def get_data (self):
				return string.join (self.buffer, '')

		def handle_connect (self):
			pass
		

class aHTTP:
		"""
			This class manages an async connection to an HTTP server.
			This should provide an identical interface as HTTP, but with
			the additional timeout variable on init controlling the timeout.
			On timeout, this will raise socket.error(ETIMEDOUT)
		"""

		def __init__(self, host = '', port = 0, timeout = 0):
				"""Initialize a new instance.

				If specified, `host' is the name of the remote host to which
				to connect.  If specified, `port' specifies the port to which
				to connect.  By default, httplib.HTTP_PORT is used.

				"""
				self.debuglevel = 0
				self.file = None
				self.send_buffer = ""
				self.connected = 0
				self.timeout = timeout
				self._request = None
				self.host = host
				self.port = port

		def set_debuglevel(self, debuglevel):
				"""Set the debug output level.

				A non-false value results in debug messages for connection and
				for all messages sent to and received from the server.

				"""
				self.debuglevel = debuglevel
		
		def connect(self, host, port = 0):
				if not self._request:
					"""Connect to a host on a given port.  """
					if not port:
							i = string.find(host, ':')
							if i >= 0:
									host, port = host[:i], host[i+1:]
									try: port = string.atoi(port)
									except string.atoi_error:
											raise socket.error, "nonnumeric port"
							else:
								port = HTTP_PORT

					# Cache DNS resolution
					try:
						host_ip = fhttplib.ip_cache[host]
					except KeyError:
						host_ip = socket.gethostbyname(host)
						fhttplib.ip_cache[host] = host_ip

					address = (host_ip, port)
					self._request = async_http_client (address)

					if self.debuglevel > 0: log ('connect:', (host, port))
		
		def throttlesendbuffer(self):
			if not self._request:
					self.connect (self.host, self.port)

			if len(self.send_buffer):
				self._request.push (self.send_buffer)
				self.send_buffer = ""

		def send(self, str):
				"""Send `str' to the server."""
				if self.debuglevel > 0: log ('send:', `str`)
				self.send_buffer = self.send_buffer + str
		
		def putrequest(self, request, selector):
				"""Send a request to the server.

				`request' specifies an HTTP request method, e.g. 'GET'.
				`selector' specifies the object being requested, e.g.
				'/index.html'.

				"""
				if not selector: selector = '/'
				str = '%s %s %s\r\n' % (request, selector, HTTP_VERSION)
##        warn(str)
				self.send(str)
		
		def putheader(self, header, *args):
				"""Send a request header line to the server.

				For example: h.putheader('Accept', 'text/html')

				"""
				str = '%s: %s\r\n' % (header, string.joinfields(args,'\r\n\t'))
##        warn(str)
				self.send(str)
		
		def endheaders(self):
				"""Indicate that the last header line has been sent to the server."""
				self.send('\r\n')
		
		def getreply(self):
				"""Get a reply from the server.
				
				Returns a tuple consisting of:
				- server response code (e.g. '200' if all goes well)
				- server response string corresponding to response code
				- any RFC822 headers in the response from the server

				"""
				# Send the data
				self.throttlesendbuffer()

				# wait for the response
				events = async_timeout_loop ()
				events.loop (self.timeout)
				if events.timedout:
					self._request.del_channel()
					raise socket.error, (errno.ETIMEDOUT, "server timed out")

				# Get the data
				self.file = cStringIO.StringIO (self._request.get_data())
				line = self.file.readline()

				if self.debuglevel > 0: log ('reply:', line)
				try:
						[ver, code, msg] = string.split(line, None, 2)
				except ValueError:
					try:
							[ver, code] = string.split(line, None, 1)
							msg = ""
					except ValueError:
							debug ("Unable to parse line: %s" % repr(line))
							debug (self._request.get_data())
							self.headers = None
							return -1, line, self.headers
				if ver[:5] != 'HTTP/':
						debug ("Unhandled version: %s" % ver)
						debug ("Unable to parse line: %s" % line)
						self.headers = None
						return -1, line, self.headers
				errcode = string.atoi(code)
				errmsg = string.strip(msg)
				self.headers = mimetools.Message(self.file, 0)
				return errcode, errmsg, self.headers
		
		def getfile(self):
				"""Get a file object from which to receive data from the HTTP server.

				NOTE:  This method must not be invoked until getreplies
				has been invoked.

				"""
				return self.file
		
		def close(self):
				"""Close the connection to the HTTP server."""
				if self.file:
						self.file.close()
				self.file = None
				if self.sock:
						self.sock.close()
				self.sock = None


def test():
		"""Test this module.

		The test consists of retrieving and displaying the Python
		home page, along with the error code and error string returned
		by the www.python.org server.

		"""
		import sys
		import getopt
		opts, args = getopt.getopt(sys.argv[1:], 'd')
		dl = 0
		for o, a in opts:
				if o == '-d': dl = dl + 1
		host = 'www.python.org'
		selector = '/'
		if args[0:]: host = args[0]
		if args[1:]: selector = args[1]
		h = HTTP()
		h.set_debuglevel(dl)
		h.connect(host)
		h.putrequest('GET', selector)
		h.endheaders()
		errcode, errmsg, headers = h.getreply()
		print 'errcode =', errcode
		print 'errmsg  =', errmsg
		print
		if headers:
				for header in headers.headers: print string.strip(header)
		print
		print h.getfile().read()


if __name__ == '__main__':
		test()
