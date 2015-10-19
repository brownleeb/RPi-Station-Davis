#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""


import os, sys, string, time, getopt
from log import *

import weather
import weather_util

class SocketUpdater(weather.Updater):
	def __init__(self, config, updateInterval=10):
		weather.Updater.__init__(self, config, updateInterval)
		self.conns = []

	def _update(self, sensor):
		now = time.localtime(time.time())
		
		t = now[3] + now[4] / 60. + now[5] / 3600.0

		## -----------------
		buf9 = [0x9f,0x43,0x82,0x28,0x39,0x11,0x27,0x9a,0x15,0x47,0x07,0x01,0x2b,0x12,0x32,0x70,0x65,0x62,0x27,0x03,0x13,0x03,0x3b,0x08,0x15,0x05,0x31,0x0a,0x14,0x40,0x38,0x00,0x00,0x06]

		buf9[0] = 0x9f
		
		itemp = weather_util.Fahrenheit2Celsius(sensor.inside_temp)
		buf9[1] = weather_util.toBCD(int((itemp*10.) % 100))
		buf9[2] = int((itemp % 100) / 10) 

		otemp = weather_util.Fahrenheit2Celsius(sensor.outside_temp)
		buf9[16] = weather_util.toBCD(int((otemp*10.) % 100))
		buf9[17] = int((otemp % 100) / 10) 
		
#    log("mybuf9", self.hexBuffer(buf9))

		checksum = 0
		for c in buf9[:-1]: checksum = checksum + c; buf9[-1] = checksum & 0xff

		## -----------------
		buf8 = [0x8f,0x24,0x44,0x14,0x03,0x3b,0x00,0x00,0x33,0x55,0x28,0x10,0x01,0x3b,0x43,0x44,0x31,0xb0,0x97,0x10,0x27,0x97,0x18,0x08,0x02,0x5b,0x02,0x31,0x31,0xb0,0x97,0x10,0x08,0x00,0x52]

		buf8[1] = weather_util.toBCD(now[5])
		buf8[2] = weather_util.toBCD(now[4])
		buf8[3] = weather_util.toBCD(now[3])
		buf8[4] = weather_util.toBCD(now[2])
		buf8[5] = now[1] & 0x0f

		buf8[8] = weather_util.toBCD(min(99, int(sensor.inside_humidity)))
		buf8[20] = weather_util.toBCD(min(99, int(sensor.outside_humidity)))

		checksum = 0
		for c in buf8[:-1]: checksum = checksum + c
		buf8[-1] = checksum & 0xff
#    log("mybuf8", self.hexBuffer(buf8))

		bufa = [0xaf,0x96,0x09,0x53,0x01,0x21,0x28,0x07,0x14,0x15,0x11,0x27,0x6a,0x00,0x83,0x10,0xb0,0x00,0x05,0x18,0x50,0x09,0x27,0x4a,0x80,0x33,0x31,0xb0,0x00,0x00,0x7b]
		bufc = [0xcf,0x12,0x20,0x02,0x00,0x30,0x08,0x54,0x30,0x11,0x30,0x12,0x28,0x5a,0x12,0x00,0x26,0x08,0x16,0x05,0x31,0x0a,0x21,0x99,0x20,0x00,0x04]
		bufb = [0xbf,0x00,0x00,0x00,0x00,0x58,0x00,0x00,0x00,0x01,0x31,0x93,0x03,0xdf]


		## -----------------

		barometer = weather_util.Inches2Millibars(sensor.barometer)
		seabarometer = weather_util.Inches2Millibars(sensor.seabarometer)

##     log("barometer", barometer)
##     log("seabarometer", seabarometer)
		bufa[1] = weather_util.toBCD(int(barometer % 100))
		bufa[2] = weather_util.toBCD(int((barometer/100) % 100))

		bufa[3] = weather_util.toBCD(int((seabarometer*10) % 100))
		bufa[4] = weather_util.toBCD(int((seabarometer/10) % 100))
		bufa[5] = weather_util.toBCD(int(seabarometer/1000))

		dp = weather_util.Fahrenheit2Celsius(sensor.dewpoint)
		bufa[7] = weather_util.toBCD(int(dp))

		checksum = 0
		for c in bufa[:-1]: checksum = checksum + c; bufa[-1] = checksum & 0xff
##    log("mybufa", self.hexBuffer(bufa))

		## -----------------

		rain = (sensor.total_rain * 2.54) * 10
#    log("rain", rain)
		bufb[5] = weather_util.toBCD(int(rain % 100))
		bufb[6] = int(rain / 100)

		checksum = 0
		for c in bufb[:-1]: checksum = checksum + c; bufb[-1] = checksum & 0xff
#    log("mybufb", self.hexBuffer(bufb))

		## -----------------

		bufc[3] = weather_util.toBCD(sensor.wind_direction / 10)
		bufc[2] = (sensor.wind_direction % 10) << 4

		wind_gust_speed = weather_util.MilesPerHour2MetersPerSecond(sensor.wind_gust_speed)
		bufc[1] = weather_util.toBCD(int(wind_gust_speed * 10 % 100))
		bufc[2] = bufc[2] | int(wind_gust_speed / 10 % 1)

#    warn("wind_direction", sensor.wind_direction)
		bufc[6] = weather_util.toBCD(sensor.wind_direction / 10)
		bufc[5] = (sensor.wind_direction % 10) << 4


		wind_speed = weather_util.MilesPerHour2MetersPerSecond(sensor.wind_speed)
		bufc[4] = weather_util.toBCD(int((wind_speed * 10) % 100))
		bufc[5] = bufc[5] | int(wind_speed / 10 % 1)

		bufc[23] = bufc[23] & (~(1<<7))
		bufc[23] = bufc[23] | ((sensor.lowbat&0x1) << 7)

		checksum = 0
		for c in bufc[:-1]: checksum = checksum + c; bufc[-1] = checksum & 0xff
#    log("mybufc", self.hexBuffer(bufc))

		## -----------------

		buf = buf9 + buf8 + bufa + bufc + bufb

		cbuf = []
		for c in buf: cbuf.append(chr(c))
		
		fp = open("currentConditions", "w")
		fp.write(string.join(cbuf, ''))
		fp.close()

	def hexBuffer(self, buffer):
		l = []
		for c in buffer:
			l.append("%02x" % c)
		return string.join(l, " ")


	def __del__(self):
		try:
			os.kill(self.pid, 9)
		except AttributeError, reason: pass
		
	def _run(self):
		hostname = ""
		port = self.config.kWeatherServerPort

		import select
		import socket

		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt (
			socket.SOL_SOCKET, socket.SO_REUSEADDR,
			1 | s.getsockopt (socket.SOL_SOCKET, socket.SO_REUSEADDR))
		s.bind((hostname, port))
		s.listen(128)

		while 1:
			r,w,e = select.select([s], [s], [], 3)

			if len(r):
				conn, addr = s.accept()
				self.conns.append(conn)

				self.sendData(conn)
			else:
				if self.conns:
#          log("sending info")
					for conn in self.conns:
						self.sendData(conn)

	def sendData(self, conn):
		fp = open("currentConditions", "r")
		buf = fp.read()
		fp.close() 
		
		try:
			conn.send(buf)
		except:
			try:
				self.conns.remove(conn)
			except ValueError: pass

	def doFork(self):
		pid = os.fork()

		if pid == 0:
			self._run()
		self.pid = pid
		return

	def run(self):
		try:
			import thread
			thread.start_new_thread(self._run, ())
		except ImportError:
			self.doFork()




def usage(progname):
	print __doc__ % vars()

def main(argv, stdout, environ):
	progname = argv[0]
	list, args = getopt.getopt(argv[1:], "", ["help"])

	if len(args) == 0:
		usage(progname)
		return
	for (field, val) in list:
		if field == "--help":
			usage(progname)
			return


if __name__ == "__main__":
	main(sys.argv, sys.stdout, os.environ)
