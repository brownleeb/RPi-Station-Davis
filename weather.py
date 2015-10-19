#!/usr/bin/python2 --

"""
usage: %(progname)s [args]

	WeatherUpdate is intended to be used with Davis Monitor II and Oregon
	Scientific WM-918 and WMR-968.  It links the Weather Stations with the
	Internet via www.wunderground.com.  
 
	Please see the config.py file for configuration information.

"""
_version = "pyweather 0.1"

import os, sys, string, time, getopt, urllib
from log import *


import serial
import weather_util

## exceptions
NoSuchWeatherStation = "No Such Weather Station"
UnsupportedStationModel = "Unsupported Station Model"
CommError = "Communication Error"


## constant
kStation_WMR968 = "WMR968"
kStation_WM918  = "WM918"
kStation_Davis  = "Davis"
kStation_Rainwise = "Rainwise"

kBaroInterval = 3600
kRainInterval = 3600
kWindInterval = 3600

kMaxInterval = max(kRainInterval, kBaroInterval, kWindInterval)

import config
try:
	import site_config
	config = site_config
except ImportError:
	pass


time_sleep = time.sleep


class Samples:
	def __init__(self):
		self.samples = []

	def addSample(self, sample, t):
		self.samples.append((t, sample))
		self.samples.sort()

	def findSample(self, t):
		ret = []
		for (t2, sample) in self.samples:
			ret.append((abs(t-t2), sample))
			
		ret.sort()

		diff, sample = ret[0]
		return diff, sample
			

	def getDiff(self, t, interval):
		diff, last_sample = self.findSample(t)

		pd1 = 1.0 * abs(diff - interval) / interval
		if pd1 <= .75: return None

		return last_sample
		
	def removeOldSamples(self, t1, t2):
		self.samples = self.getSamples(t1, t2)
		return


	def getSamples(self, t1, t2):
		new_samples = []
		for (t, sample) in self.samples:
			if t >= t1 and t <= t2: new_samples.append((t, sample))
		
		return new_samples


	def CalculateDerivatives(self, now, si):
		## calculate derivatives
		sample = self.getDiff(now-kRainInterval, kRainInterval)
		if sample:
			si.rain_diff = si.total_rain - sample.total_rain

		sample = self.getDiff(now-kBaroInterval, kBaroInterval)
		if sample:
			si.baro_diff = si.barometer - sample.barometer

		## calc max/min wind speed
		wind_samples = self.getSamples(now - kWindInterval, now)
		wind_speed = []
		outside_temp = []
		outside_humidity = []

		for (t, sample) in wind_samples:
			wind_speed.append(sample.wind_speed)
			outside_temp.append(sample.outside_humidity)
			outside_humidity.append(sample.outside_temp)
		wind_speed.sort()
		outside_temp.sort()
		outside_humidity.sort()

		si.max_wind_speed = wind_speed[-1]
		si.min_wind_speed = wind_speed[0]

		si.max_outside_temp = outside_temp[-1]
		si.min_outside_temp = outside_temp[0]

		si.max_outside_humidity = outside_humidity[-1]
		si.min_outside_humidity = outside_humidity[0]



class SensorImage:
	def __init__(self):
		self.sample_time = 0

		self.inside_temp = 0.0
		self.outside_temp = 0.0
		self.basement_temp = 0.0
		self.wind_speed = 0.0
		self.wind_gust_speed = 0.0
		self.wind_direction = 0
		self.barometer = 0.0
		self.seabarometer = 0.0
		self.inside_humidity = 0.0
		self.outside_humidity = 0.0
		self.basement_humidity = 0.0
		self.total_rain = 0.0

		self.dewpoint = 0.0

		self.lowbat = 0

		self.rain_diff = 0
		self.baro_diff = 0

		self.max_wind_speed = None
		self.min_wind_speed = None

		self.max_outside_temp = None
		self.min_outside_temp = None

		self.max_outside_humidity = None
		self.min_outside_humidity = None
		
		
	def display(self):
		s = "itemp: %.1f otemp: %.1f wind: %s@%s baro:%.3f ihum: %s%% ohum: %s%%  rain: %.2f\ndewpoint: %.2f" % (self.inside_temp, self.outside_temp, self.wind_speed, self.wind_direction, self.barometer, self.inside_humidity, self.outside_humidity, self.total_rain, self.dewpoint)
		return s

	def Display(self):
		if self.baro_diff == 0:
			baro_change = " "
		else:
			if   self.baro_diff > 0.03: baro_change = "^" 
			elif self.baro_diff < -0.03: baro_change = "V"
			else: baro_change = "-"

#		log(" Inside Temperature: %-6.1f F   Inside Humidity: %3s%%" % (self.inside_temp, self.inside_humidity))
#		log("Outside Temperature: %-6.1f F  Outside Humidity: %3s%%" % (self.outside_temp, self.outside_humidity))
#		log("          Barometer: %-6.3f %s              Wind: %.1f@%3s " % (self.barometer, baro_change, self.wind_speed, self.wind_direction, ))
#		log("           Dewpoint: %-6.2f F" % self.dewpoint)
#		log("               Rain: %.2f (in)" % self.rain_diff)
#		log("         Total Rain: %.2f (in)" % self.total_rain)
#		log("-")
		
class Updater:
	def __init__(self, config, updateInterval=10):
		self.config = config
		self.lastupdate = 0
		self.updateInterval = updateInterval

	def update(self, sensor):
		now = time.time()
		
		if self.lastupdate + self.updateInterval <= now:
			self.lastupdate = now
			self._update(sensor)

class ShellUpdate(Updater):
	def _update(self, sensor):
		sensor.Display()

class CSVUpdate(Updater):
	def _update(self, sensor):
		t = time.localtime(sensor.sample_time)
		
		line = [t[0], t[1], t[2], t[3], t[4], t[5]]
		line.append(sensor.wind_speed)
		line.append(sensor.wind_gust_speed)
		line.append(sensor.wind_direction)
		line.append(sensor.inside_humidity)
		line.append(sensor.outside_humidity)
		line.append(sensor.inside_temp)
		line.append(sensor.outside_temp)
		line.append(sensor.barometer)
		line.append(sensor.total_rain)
		line.append(sensor.total_rain)
		line.append(sensor.rain_diff)
		line.append(sensor.basement_temp)
		line.append(sensor.basement_humidity)
		line.append(0)
		
		if os.path.isfile(config.kCSVFile):
			fp = open(self.config.kCSVFile)
			lines = fp.readlines()
			fp.close()
			if len(lines) >= config.kCSV_MaxLines:
				st = len(lines) - config.kCSV_MaxLines + 1
				fp = open(config.kCSVFile, "w")
				fp.writelines(lines[st:])
				fp.close()

		if os.path.isfile(config.kCSVFile):
			fp = open(self.config.kCSVFile, "a")
		else:
			fp = open(self.config.kCSVFile, "w")
		sline = []
		for num in line: sline.append(str(num))
		fp.write(string.join(sline, ","))
		fp.write(os.linesep)
		fp.close()
		
		
class Wunderground(Updater):

	def _update(self, sensor):
		if self.config.kWundergroundUserID == 'userid': return

		if sensor.sample_time == 0: 
			warn("sample_time is zero")
			return

		utc = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(sensor.sample_time))

		host = "weatherstation.wunderground.com"
		port = 80
		inside_cond = "Inside=%.1f/%s%%" % (sensor.inside_temp, sensor.inside_humidity)

		path = "/weatherstation/updateweatherstation.php?ID=%s&PASSWORD=%s&dateutc=%s&winddir=%s&windspeedmph=%s&windgustmph=%s&tempf=%.1f&rainin=%.2f&baromin=%.2f&dewptf=%.2f&humidity=%s&indoortempf=%.1f&indoorhumidity=%s&softwaretype=%s&action=updateraw" % (urllib.quote(self.config.kWundergroundUserID), urllib.quote(self.config.kWundergroundPassword), urllib.quote(utc), sensor.wind_direction, sensor.wind_speed, sensor.max_wind_speed, sensor.outside_temp, sensor.rain_diff, sensor.barometer, sensor.dewpoint, sensor.outside_humidity, sensor.inside_temp, sensor.inside_humidity, urllib.quote(_version))

		url = "http://" + host + path

		if 1:
			try:  
#				sleep_time = (((time.localtime(time.time())[4] / config.kWunderground_UpdateInterval) + 1) * config.kWunderground_UpdateInterval);
#				if sleep_time > 59: sleep_time = 60 - time.localtime(time.time())[4];
#				else: sleep_time = sleep_time - time.localtime(time.time())[4];
#				sleep_seconds = time.localtime(time.time())[5];
#				sleep_time = (sleep_time * 60) - sleep_seconds;
#				m, s = divmod(sleep_time, 60);
#				log("uploading to Wunderground.com.  Next update in: " + str(m) + ":" + str(s));
				log("uploading to Wunderground.com.");

				if 1:
					import fhttplib
					h = fhttplib.aHTTP (host, port, timeout=10)

					h.putrequest("GET", path)
					h.putheader("Host", host)
					h.endheaders()

					errcode, errmsg, headers = h.getreply()

					f = h.getfile()
					page = f.read()
					f.close()

				if 0:
					fp = urllib.urlopen(url)
					page = fp.read()
					fp.close()
			except:
				import traceback
				traceback.print_exc()



def run():
	try:
		config.kStationType
	except AttributeError:
		print "Configuration Error:"
		print
		print "Please edit the config.py file and choose a Station Type. ('kStationType')"
		return

	try:
		config.kCommPort
	except AttributeError:
		print "Configuration Error:"
		print
		print "Please edit the config.py file and pick a Serial Port ('kCommPort')."
		return

	if config.kWundergroundUserID == "userid":
		print "Configuration Error:"
		print
		print "Please edit the config.py file and enter your Wunderground "
		print "Person Weather Station Userid and Password.  To sign up, "
		print "visit: http://www.wunderground.com/weatherstation/usersignup.asp"
		print
		return
	
	if config.kStationType == kStation_Davis:
		import station_davis
		module = station_davis
	elif config.kStationType == kStation_Rainwise:
		import station_rainwise
		module = station_rainwise
	elif config.kStationType == kStation_WM918:
		import station_wm918
		module = station_wm918
	elif config.kStationType == kStation_WMR968:
		import station_wmr968
		module = station_wmr968

	log("acquiring Serial Port")
	cfg = module.GetSerialConfig(config)
	port = serial.open(cfg)
	wl = module.DataLogger(config, port)

#	sleep_time = ((time.localtime(time.time())[4] / config.kWunderground_UpdateInterval) + 1) * config.kWunderground_UpdateInterval
#	if sleep_time > 59: sleep_time = 60 - time.localtime(time.time())[4]
#	else: sleep_time = sleep_time - time.localtime(time.time())[4]
#	sleep_seconds = time.localtime(time.time())[5]
#	log("Next update: " + str(sleep_seconds) + " seconds")
#	wl.SetUpdater(Wunderground(config, ((sleep_time * 60) - sleep_seconds)))
	wl.SetUpdater(Wunderground(config, config.kWunderground_UpdateInterval))
	wl.SetUpdater(CSVUpdate(config, config.kCSV_UpdateInterval))
	wl.SetUpdater(ShellUpdate(config, config.kShell_UpdateInterval))

	if config.kWeatherServer:
		import weatherServer
		su = weatherServer.SocketUpdater(config, 5)
		wl.SetUpdater(su)
		su.run()

	try:
		while 1:
			try:
				wl.StartLoop()
			except serial.TimeoutError, msg:
				log("timeout error - pi")
				import traceback
				traceback.print_exc()
				log(msg)
			except CommError, msg:
				log("comm error - pi")
				import traceback
				traceback.print_exc()
				log("Communicatons Error", msg)
	finally:
		port.close()
	


def usage(progname):
	print __doc__ % vars()

def main(argv=sys.argv, stdout=sys.stdout, environ=os.environ):
	progname = argv[0]
	list, args = getopt.getopt(argv[1:], "", ["help"])

	for (field, val) in list:
		if field == "--help":
			usage(progname)
			return

	debugfull()

	while 1:
		try:  
			run()
		except KeyboardInterrupt:
			import traceback
			traceback.print_exc()
			return
		except:
			import traceback
			traceback.print_exc()
			if sys.platform == "win32":
				time.sleep(20)

if __name__ == "__main__":
	main(sys.argv, sys.stdout, os.environ)

