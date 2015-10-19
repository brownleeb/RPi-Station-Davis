#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""


import os, sys, string, time, getopt, types

from common import *

import unixserial

if sys.platform in ("win32", ):
	import winserial
##  from winserial import *
	serial_module = winserial
elif string.find(sys.platform, "linux") != -1:
##  from unixserial import *
	import unixserial
	serial_module = unixserial
elif sys.platform in ("mac", ):
##	from macserial import *
	import macserial
	serial_module = macserial
else:
  raise ImportError, "unknown platform"

def open(cfg):
	serial_module = unixserial
	serialport = cfg['port']
        print(serial_module)
	port = None

	if type(serialport) == types.IntType:
		port = serial_module.Port()
	elif type(serialport) == types.StringType:
		if not serialport:
			raise SerialError, "invalid serial port"

		if serialport[0] == "/":
			port = serial_module.Port()
		elif string.find(serialport, ":") != -1:
			import tcpserial
			serial_module = tcpserial

			port = serial_module.Port()

	port.open(cfg)
	return port
			
			
		
	

def test():
  cfg = PortDict()
  cfg['port'] = COM2
  cfg['baud'] = Baud2400
  cfg['dataBits'] = WordLength8
  cfg['parity'] = NoParity
  cfg['stopBits'] = OneStopBit

  s = Port()
  s.open(cfg)
  s.close()
  
def usage(progname):
  print __doc__ % vars()

def main(argv, stdout, environ):
  progname = argv[0]
  list, args = getopt.getopt(argv[1:], "", ["help", "test"])

  for (field, val) in list:
    if field == "--help":
      usage(progname)
      return
    if field == "--test":
      debugfull()
      test()
      return


if __name__ == "__main__":
  main(sys.argv, sys.stdout, os.environ)


