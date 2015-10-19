#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""


import os, sys, string, time, getopt
from log import *

import struct

import serial
import weather
import weather_util
from weather_util import fromBCD, toBCD

gDavisModels = {}
gDavisModels[0] = "Davis Wizard III"
gDavisModels[1] = "Davis Wizard II"
gDavisModels[2] = "Davis Monitor II"
gDavisModels[3] = "Davis Perception"
gDavisModels[4] = "Davis GroWeather"
gDavisModels[5] = "Davis Energy"
gDavisModels[6] = "Davis Health"

ACK = 6


class DataLogger:
	def __init__(self, config, port):
		self.port = port
		self.config = config

		self.updaters = []

		self.tp1cal = 0
		self.tp2cal = 0
		self.rncal = 100
		self.hm1cal = 0
		self.hm2cal = 0
		self.barcal = 0
		self.windcal = 0

	def SetUpdater(self, updater):
		self.updaters.append(updater)

	def get_acknowledge(self):
		c = self.port.read(1, timed=1)

		if ord(c) != ACK:
			raise weather.CommError

	def ReadWRD(self, n, bank, addr):
		if bank == 0: bankval = 2
		elif bank == 1: bankval = 4
		self.port.write("WRD" + chr((n << 4) | bankval) + chr(addr & 0x00ff) + chr(0xd))
		self.get_acknowledge()

		data = self.port.read((n+1)/2, timed=1)
		return data

	def ReadByte(self, bank, addr):
		bytes = self.ReadWRD(2, bank, addr)
		rec = struct.unpack('<b', bytes)
		n = rec[0]
		return n

	def ReadWord(self, bank, addr):
		bytes = self.ReadWRD(4, bank, addr)
		rec = struct.unpack('<h', bytes)
		n = rec[0]
		return n

	def WriteWord(self, bank, addr, n):
		bytes = struct.pack('<h', n)
		self.WriteWRD(4, bank, addr, bytes)

	def WriteWRD(self, n, bank, addr, data):
		if bank == 0: bankval = 1
		elif bank == 1: bankval = 3
		self.port.write("WWR" + chr((bankval) | (n << 4)) + chr(addr & 0x00ff) + data + chr(0xd))
		self.get_acknowledge()



	def SendSTART(self):
		self.port.write("START" + chr(0x0d))
		self.get_acknowledge()

	def SendLOOP(self):
#		self.port.write("LOOP" + chr(0) + chr(1) + chr(0x0d))
		self.port.write("LOOP" + chr(255) + chr(255) + chr(0x0d))
		self.get_acknowledge()

	def ReadLOOPResponse(self):
		c = self.port.read(1, timed=1)
		if ord(c) != 1:
			raise weather.CommError, "Invalid Header %s" % ord(c)

		s = self.port.read(17, timed=1)

		if len(s) != 17: 
			raise weather.CommError, "Invalid Length of Response to LOOP: len %d" % len(s)
		if compute_crc(s): 
			raise weather.CommError, "CRC Error of Response to LOOP"

		si = weather.SensorImage()
		self.ParseLoopResponse(si, s)

		return si


	def ParseLoopResponse(self, si, s):
		if len(s) != 17: warn("wrong size", len(s))
		rec = struct.unpack('<hhBhhBBhhh', s)

		si.sample_time = time.time()
		si.inside_temp = (rec[0] + self.tp1cal) / 10.
		si.outside_temp = (rec[1] + self.tp2cal) / 10.
		si.wind_speed = (rec[2] * 1600.) / self.windcal
		si.wind_gust_speed = si.wind_gust_speed
		si.wind_direction = rec[3] 
		si.barometer = (rec[4] + 370) / 1000.
		si.seabarometer = si.barometer

		si.inside_humidity = rec[5] + self.hm1cal
		si.outside_humidity = rec[6] + self.hm2cal
		if si.outside_humidity > 100: si.outside_humidity = 100
		si.total_rain = rec[7] / (1.0 * self.rncal)

		si.dewpoint = weather_util.DewCalc(si.outside_humidity, si.outside_temp)

		crc = rec[8]
		

	def ReadTime(self):
		d = self.ReadWRD(6, 1, 0xBE)
		hour = fromBCD(ord(d[0:1]))
		min = fromBCD(ord(d[1:2]))
		sec = fromBCD(ord(d[2:3]))

		d = self.ReadWRD(3, 1, 0xC8)
		day = fromBCD(ord(d[0:1]))
		month = ord(d[1])

		return month, day, hour, min, sec

	def SetTime(self, t):
		self.ReadTime()

		(year, month, day, hour, min, sec, d,d,d) = time.localtime(t)

		self.WriteWRD(6, 1, 0xBE, chr(toBCD(hour)) + chr(toBCD(min)) + chr(toBCD(sec)))

		self.WriteWRD(3, 1, 0xC8, chr(toBCD(day)) + chr(month))

	def GetCalibration(self):
		self.tp1cal = self.ReadWord(1, 0x0152)
		self.tp2cal = self.ReadWord(1, 0x0178)
		self.rncal = self.ReadWord(1, 0x01D6)
		self.hm1cal = 0
		self.hm2cal = self.ReadWord(1, 0x01DA)
		self.barcal = self.ReadWord(1, 0x012C)
		self.windcal = 1600

#		warn("-" * 50)
#		warn("Inside Temperature Calibration:", self.tp1cal/10., "degrees")
#		warn("Outside Temperature Calibration:", self.tp2cal/10., "degrees")
#		warn("Rain Sensor Calibration:", self.rncal, "clicks per inch")
#		warn("Inside Humidity Calibration", self.hm1cal, "%")
#		warn("Outside Humidity Calibration", self.hm2cal, "%")
#		warn("Barometric Pressure Calibration Offset", self.hm2cal)
#		warn("Wind Calibration Offset", self.windcal)
#		warn("-" * 50)

	def SetCalibration(self, tp1cal, tp2cal, rncal, h2mcal, barcal):
		self.WriteWord(1, 0x0152, tp1cal)
		self.WriteWord(1, 0x0178, tp2cal)
		self.WriteWord(1, 0x01D6, rncal)
		self.WriteWord(1, 0x01DA, h2mcal)
		self.WriteWord(1, 0x012C, barcal)


	def GetModelNumber(self):
		modelno = self.ReadWRD(1, 0, 0x004D)
		modelno = ord(modelno)

		try:
			model = gDavisModels[modelno]
		except KeyError:
			raise weather.NoSuchWeatherStation, modelno
		
		warn("model", model)

		return model, modelno
		
	def StartLoop(self):
#		self.port.flush()

		try:
			model, modelno = self.GetModelNumber()
		except serial.TimeoutError, msg:
			log(msg)
			return
			
		if modelno != 2:
			raise weather.UnsupportedStationModel, modelno

		self.SetTime(time.time())

##		self.SetCalibration(0, 0, 100, 0, 0)
		self.GetCalibration()

		self.SendSTART()

		samples = weather.Samples()

		while 1:
			self.SendLOOP()

			now = time.time()
			si = self.ReadLOOPResponse()

			samples.addSample(si, now)

			samples.CalculateDerivatives(now, si)
			samples.removeOldSamples(now - weather.kMaxInterval, now)

			## update sample
			if self.updaters:
				for updater in self.updaters:
					updater.update(si)

			weather.time_sleep(self.config.kUpdateInterval)



crc_table = [
0x0,  0x1021,  0x2042,  0x3063,  0x4084,  0x50a5,  0x60c6,  0x70e7,  
0x8108,  0x9129,  0xa14a,  0xb16b,  0xc18c,  0xd1ad,  0xe1ce,  0xf1ef,  
0x1231,  0x210,  0x3273,  0x2252,  0x52b5,  0x4294,  0x72f7,  0x62d6,  
0x9339,  0x8318,  0xb37b,  0xa35a,  0xd3bd,  0xc39c,  0xf3ff,  0xe3de,  
0x2462,  0x3443,  0x420,  0x1401,  0x64e6,  0x74c7,  0x44a4,  0x5485,  
0xa56a,  0xb54b,  0x8528,  0x9509,  0xe5ee,  0xf5cf,  0xc5ac,  0xd58d,  
0x3653,  0x2672,  0x1611,  0x630,  0x76d7,  0x66f6,  0x5695,  0x46b4,  
0xb75b,  0xa77a,  0x9719,  0x8738,  0xf7df,  0xe7fe,  0xd79d,  0xc7bc,  
0x48c4,  0x58e5,  0x6886,  0x78a7,  0x840,  0x1861,  0x2802,  0x3823,  
0xc9cc,  0xd9ed,  0xe98e,  0xf9af,  0x8948,  0x9969,  0xa90a,  0xb92b,  
0x5af5,  0x4ad4,  0x7ab7,  0x6a96,  0x1a71,  0xa50,  0x3a33,  0x2a12,  
0xdbfd,  0xcbdc,  0xfbbf,  0xeb9e,  0x9b79,  0x8b58,  0xbb3b,  0xab1a,  
0x6ca6,  0x7c87,  0x4ce4,  0x5cc5,  0x2c22,  0x3c03,  0xc60,  0x1c41,  
0xedae,  0xfd8f,  0xcdec,  0xddcd,  0xad2a,  0xbd0b,  0x8d68,  0x9d49,  
0x7e97,  0x6eb6,  0x5ed5,  0x4ef4,  0x3e13,  0x2e32,  0x1e51,  0xe70,  
0xff9f,  0xefbe,  0xdfdd,  0xcffc,  0xbf1b,  0xaf3a,  0x9f59,  0x8f78,  
0x9188,  0x81a9,  0xb1ca,  0xa1eb,  0xd10c,  0xc12d,  0xf14e,  0xe16f,  
0x1080,  0xa1,  0x30c2,  0x20e3,  0x5004,  0x4025,  0x7046,  0x6067,  
0x83b9,  0x9398,  0xa3fb,  0xb3da,  0xc33d,  0xd31c,  0xe37f,  0xf35e,  
0x2b1,  0x1290,  0x22f3,  0x32d2,  0x4235,  0x5214,  0x6277,  0x7256,  
0xb5ea,  0xa5cb,  0x95a8,  0x8589,  0xf56e,  0xe54f,  0xd52c,  0xc50d,  
0x34e2,  0x24c3,  0x14a0,  0x481,  0x7466,  0x6447,  0x5424,  0x4405,  
0xa7db,  0xb7fa,  0x8799,  0x97b8,  0xe75f,  0xf77e,  0xc71d,  0xd73c,  
0x26d3,  0x36f2,  0x691,  0x16b0,  0x6657,  0x7676,  0x4615,  0x5634,  
0xd94c,  0xc96d,  0xf90e,  0xe92f,  0x99c8,  0x89e9,  0xb98a,  0xa9ab,  
0x5844,  0x4865,  0x7806,  0x6827,  0x18c0,  0x8e1,  0x3882,  0x28a3,  
0xcb7d,  0xdb5c,  0xeb3f,  0xfb1e,  0x8bf9,  0x9bd8,  0xabbb,  0xbb9a,  
0x4a75,  0x5a54,  0x6a37,  0x7a16,  0xaf1,  0x1ad0,  0x2ab3,  0x3a92,  
0xfd2e,  0xed0f,  0xdd6c,  0xcd4d,  0xbdaa,  0xad8b,  0x9de8,  0x8dc9,  
0x7c26,  0x6c07,  0x5c64,  0x4c45,  0x3ca2,  0x2c83,  0x1ce0,  0xcc1,  
0xef1f,  0xff3e,  0xcf5d,  0xdf7c,  0xaf9b,  0xbfba,  0x8fd9,  0x9ff8,  
0x6e17,  0x7e36,  0x4e55,  0x5e74,  0x2e93,  0x3eb2,  0xed1,  0x1ef0,  
]

def compute_crc(str):
	accum = 0L
	for c in str:
		accum_high = (accum & 65280) / 256
		comb_val = int(accum_high) ^ ord(c)
		crc_tbl = long(crc_table[comb_val])
		accum_low = (accum & 255) * 256
		accum = accum_low ^ crc_tbl
	return int(accum)
	


def GetSerialConfig(pConfig):
	cfg = serial.PortDict()
	
	cfg.set(pConfig.kCommPort, serial.Baud2400, 
					serial.WordLength8, serial.NoParity, serial.OneStopBit, 5000)
	return cfg
	

