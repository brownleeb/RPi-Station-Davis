#! /usr/local/bin/python --

import os, sys, string, time, getopt, types, re

TRUE = 1
FALSE = 0
PORT_CLOSED = None

TimeoutError = "TimeoutError"
SerialError = "SerialError"
UnimplementedError = 'UnimplementedError'

COM1 = 0
COM2 = 1
COM3 = 2
COM4 = 3
COM5 = 4
COM6 = 5
COM7 = 6
COM8 = 7
COM9 = 8

Mode_Raw = 0
Mode_Flow = 1

Baud110 = 110 
Baud300 = 300
Baud600 = 600
Baud1200 = 1200
Baud2400 = 2400
Baud4800 = 4800
Baud9600 = 9600
Baud19200 = 19200
Baud38400 = 38400
Baud57600 = 57600
Baud115200 = 115200

NoParity = 0
OddParity = 1
EvenParity = 2
MarkParity = 3
SpaceParity = 4

OneStopBit = 0
TwoStopBits = 1

WordLength5 = 5
WordLength6 = 6
WordLength7 = 7
WordLength8 = 8

RSP_NONE = 0
RSP_TERMINATED = 1
RSP_FIXEDLEN = 2
RSP_BEST_EFFORT = 3




class PortDict:

		"""A dictionary used to parameterize a Port object.

		Usage:  import serial
				d = serial.PortDict()
				d['port'] = serial.COM2
				...
				fd = serial.Port()
				fd.open(d)

		Entries (keys are all strings):
				debug:        Boolean, turn on/off debug/tracing
				port:         Port param COM1 ... Com9
				baud:         Port param, Baud110|Baud300|Baud1200|Baud2400|Baud4800
											|Baud9600|Baud19200|Baud38400|Baud57600|Baud115200
				parity:       Port param, NoParity|OddParity|EvenParity|MarkParity
											|SpaceParity 
				stopBits:     Port param, OneStopBit|TwoStopBits
				dataBits:     Port param, WordLength5|WordLength6|WordLength7
											|WordLength8

				rxBufSize:    Maximum size of a rsp
				rxBufSize:    Maximum size of a cmd

				timeOutMs:    Milliseconds to wait for expected responses

				cmdsEchoed:   Boolean, whether hdw echoes characters or not
				cmdTerm:      String expected to terminate RSP_TERMINATED command
											responses
				rspTerm:      String appended to cmd's
				rspType:      Used by cmd methods, RSP_NONE|RSP_TERMINATED|RSP_FIXEDLEN
											|RSP_BEST_EFFORT
				rspFixedLen:  Length of expected rsp, if rspType == RSP_FIXEDLEN

		"""

		portKw = {
				COM1: 'COM1',
				COM2: 'COM2',
				COM3: 'COM3',
				COM4: 'COM4',
				COM5: 'COM5',
				COM6: 'COM6',
				COM7: 'COM7',
				COM8: 'COM8',
				COM9: 'COM9'
				}

		modeKw = {
			Mode_Flow: "Mode_Flow",
			Mode_Raw: "Mode_Raw"
			}

		baudKw = {
				Baud110: 'Baud110',
				Baud300: 'Baud300',
				Baud600: 'Baud600',
				Baud1200: 'Baud1200',
				Baud2400: 'Baud2400',
				Baud4800: 'Baud4800',
				Baud9600: 'Baud9600',
				Baud19200: 'Baud19200',
				Baud38400: 'Baud38400',
				Baud57600: 'Baud57600',
				Baud115200: 'Baud115200'
				}
		parityKw = {
				NoParity: 'NoParity',
				OddParity: 'OddParity',
				EvenParity: 'EvenParity',
				MarkParity: 'MarkParity',
				SpaceParity: 'SpaceParity'
				}
		stopBitsKw = {
				OneStopBit: 'OneStopBit',
				TwoStopBits: 'TwoStopBits'
				}
		dataBitsKw = {
				WordLength5: 'WordLength5',
				WordLength6: 'WordLength6',
				WordLength7: 'WordLength7',
				WordLength8: 'WordLength8'
				}
		rspTypeKw = {
				RSP_NONE: 'RSP_NONE',
				RSP_TERMINATED: 'RSP_TERMINATED',
				RSP_FIXEDLEN: 'RSP_FIXEDLEN',
				RSP_BEST_EFFORT: 'RSP_BEST_EFFORT'
				}
		paramKws = {
				'port': portKw,
				'baud': baudKw,
				'mode': modeKw,
				'parity': parityKw,
				'stopBits': stopBitsKw,
				'dataBits': dataBitsKw,
				'rspType': rspTypeKw
				}

		portVals = tuple(portKw.keys())
		baudVals = tuple(baudKw.keys())
		modeVals = tuple(modeKw.keys())
		parityVals = tuple(parityKw.keys())
		stopBitVals = tuple(stopBitsKw.keys())
		dataBitVals = tuple(dataBitsKw.keys())
		rspTypeVals = tuple(rspTypeKw.keys())

		def __init__(self):
				"""Create a serial port configuration dictionary that can be modified
				before passing to the Port.open method.

				"""
				self._dict = {}
				self._dict['nonblock'] = FALSE
				self._dict['debug'] = FALSE
				self._dict['port'] = COM2
				self._dict['baud'] = Baud9600
				self._dict['mode'] = Mode_Flow
				self._dict['parity'] = NoParity
				self._dict['stopBits'] = OneStopBit
				self._dict['dataBits'] = WordLength8
				self._dict['rxBufSize'] = 1024
				self._dict['txBufSize'] = 1024
				self._dict['timeOutMs'] = 500
				self._dict['cmdsEchoed'] = FALSE
				self._dict['cmdTerm'] = ''
				self._dict['rspTerm'] = ''
				self._dict['rspTermPat'] = None
				self._dict['rspType'] = RSP_BEST_EFFORT
				self._dict['rspFixedLen'] = 0

		def set(self, port, baud=None, dataBits=None, parity=None, 
						stopBits=None, timeOutMs=None):

			self['port'] = port

			if baud is not None: 
				self['baud'] = baud
			if dataBits is not None: 
				self['dataBits'] = dataBits
			if parity is not None: 
				self['parity'] = parity
			if stopBits is not None: 
				self['stopBits'] = stopBits
			if timeOutMs is not None: 
				self['timeOutMs'] = timeOutMs

		def setDevice(self, path):
			self['device'] = path

		def __getitem__(self, key):
				"""Normal dictionary behavior."""
				return self._dict[key]

		def __setitem__(self, key, value):
				"""Only allow existing items to be changed.  Validate entries"""
				if self._dict.has_key(key):
						if key == 'baud':
							if not value in PortDict.baudVals:
								raise AttributeError, 'Illegal baud value'
						elif key == 'mode':
								if not value in PortDict.modeVals:
										raise AttributeError, 'Illegal mode value'
						elif key == 'parity':
								if not value in PortDict.parityVals:
										raise AttributeError, 'Illegal parity value'
						elif key == 'stopBits':
								if not value in PortDict.stopBitVals:
										raise AttributeError, 'Illegal stopBits value'
						elif key == 'dataBits':
								if not value in PortDict.dataBitVals:
										raise AttributeError, 'Illegal dataBits value'
						elif key == 'rspType':
								if not value in PortDict.rspTypeVals:
										raise AttributeError, 'Illegal rspType value'
						elif key == 'rxBufSize' or key == 'txBufSize':
								if value <= 0:
										raise AttributeError, 'buffer size must be > 0'
						elif key == 'timeOutMs':
								if value <= 0 or value > 60000:
										raise AttributeError, '0 < timeOutMs <= 60000'
						elif key == 'cmdTerm' or key == 'rspTerm':
								if type(value) != StringType:
										raise AttributeError, 'terminators must be strings'
						elif key == 'rspTermPat':
								raise AttributeError, 'cannot set rspTermPat directly,'\
											'store rspTerm instead'
						elif key == 'rspFixedLen':
								if value <= 0 or value > self._dict['rxBufSize']:
										raise AttributeError, \
													'0 < rspFixedLen <= %d' % self._dict['rxBufSize']
						elif key == 'debug' or key == 'cmdsEchoed':
								if type(value) != IntType:
										raise AttributeError, 'must be a boolean value'
						self._dict[key] = value
						if key == 'rspTerm':
								self._dict['rspTermPat'] = re.compile('^.*%s$' % value)
				else:
						raise KeyError, 'No such key %s in a PortDict' % key

		def has_key(self, key):
				"""Normal dictionary behavior."""
				return self._dict.has_key(key)

		def keys(self):
				"""Normal dictionary behavior."""
				return self._dict.keys()

		def __repr__(self):
				"""Format a listing of current options."""
				str = '<serial Config:'
				keys = self._dict.keys()
				keys.sort()
				for k in keys:
						if PortDict.paramKws.has_key(k):
								d = PortDict.paramKws[k]
								str = str + '\n   %s = %s' % (k, d[self._dict[k]])
						else:
								str = str + '\n   %s = %s' % (k, `self._dict[k]`)
				str = str + '\n>\n'
				return str
