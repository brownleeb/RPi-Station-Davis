#!/usr/bin/env python

import os, sys, time, string, socket

"""
class: Logger
desc: gives automatic log rotation and logging to a file for all modules
			using the log.py logging functions
			 
example: 
	l = Logger("logger", recyclePeriod=kDayPeriod)
	This will log everything to stderr and also to the log file
	 
notes: 
	- behavior is that second logger class instantiation will take over (and
		close) the first logger
	- Also could add filename formatting -- some interest
	items to add would be pid, machinename
"""

kRotate = 0
kOverwrite = 1
kAppend = 2

# cycle
kMaxCycle = 10

# period
kHourPeriod = 3600
kDayPeriod = 86400
kWeekPeriod = 86400 * 7

kDefaultLogPath = "/var/tmp/log"

LoggerError = "Only one Logger is allowed"

class Logger:
	_Logger = None

	def __init__ (self, name, loggerType=kRotate, 
								recyclePeriod=kDayPeriod, 
								logPath=kDefaultLogPath, debug=0):
		Logger._Logger = self

		self._file = None
		self._debug = debug
		self._name = name
		self._loggerType = loggerType
		self._logPath = logPath
		self._recyclePeriod = recyclePeriod
		self._startTime = None
		self._checkFlag = 0
		self._host = socket.gethostname()

		self.recycle()

	def __del__(self): 
		if self._debug: warn ("-- In del --")
		if self._file: self._file.close()

	def logPath(self): return self._logPath
	def recyclePeriod(self): return self._recyclePeriod
	def debug(self): return self._debug
	def checkFlag(self): return self._checkFlag
	def checkFlag_(self,v): self._checkFlag = v; return self

	def write(self,s):
		if self._file: self._file.write(s)

	def getFileHandle(self):
		if self._loggerType == kAppend:
			oarg = 'a'
		else:
			oarg = 'w'
		f = open(os.path.join(self.logPath(), self.filename()), oarg, 0) # unbuffered
		return f

	def filename (self, i=""):
		if i:
			return "%s.%s" % (self._name, i)
		else:
			return self._name

	def recycle(self):
		self.checkFlag_(0)
		self._startTime = time.time()

		warn("Recycling %s on '%s' logging to %s" % (self._name, self._host, 
																								 os.path.join(self.logPath(), self.filename())))

		if self._loggerType == kRotate:
			self.rotate()

		if self._file: self._file.close()
		self._file = self.getFileHandle()
		#sys.stdout = self._file
		self.checkFlag_(1)
		return

	def rotate(self):
		"""rotates to filename.1 to filename.kMaxCycle"""
		if self.logPath():
			os.chdir (self.logPath())

		ra = range(0,kMaxCycle)
		ra.reverse()
		if self._debug: warn("Rotating '%s' files" % self._name)
		for i in ra:
			if i:
				oldname = self.filename(str(i))
			else:
				oldname = self.filename()
			newname = self.filename(str(i + 1))
			if os.path.exists(oldname):
				if self._debug:
					warn ("Rotating %s => %s file" % (oldname,newname))
				os.rename(oldname, newname)
				
	def check(self, t):
		if not self.checkFlag(): 
			return
		if self._debug:
			sys.stderr.write ('time left: %d of %d \n' % (self.recyclePeriod() - (t - self._startTime), self.recyclePeriod()))
		if (t - self._startTime) > self.recyclePeriod():
			self.recycle()

#----------------------------------------------------------------------
# static functions

_gDebug = 0
_gFileDebug = 0

kBLACK = 0
kRED = 1
kGREEN = 2
kYELLOW = 3
kBLUE = 4
kMAGENTA = 5
kCYAN = 6
kWHITE = 7
kBRIGHT = 8

def ansicolor (str, fgcolor = None, bgcolor = None):
	o = ""
	if fgcolor:
		if fgcolor & kBRIGHT:
			bright = ';1'
		else:
			bright = ''
		o = o + '%c[3%d%sm' % (chr(27), fgcolor & 0x7, bright)
	if bgcolor:
		o = o + '%c[4%dm' % (chr(27), bgcolor)
	o = o + str
	if fgcolor or bgcolor:
		o = o + '%c[0m' % (chr(27))
	return o


def _log(*args):
	t = time.time()

	log_line = ""

	log_line = log_line + "[" + time.strftime("%m/%d %H:%M:%S", time.localtime(t)) + "] "

	l = []
	for arg in args:
		l.append(str(arg))
	log_line = log_line + string.join(l, " ") + "\n"

	if Logger._Logger: 
		Logger._Logger.check(t)
		Logger._Logger.write(log_line)
		
	sys.stderr.write(log_line)

def warn(*args):
	apply(_log, args)

def warnred(*args):
	args = tuple (["[31m"] + list(args) + ["[0m"])
	apply(_log, args)

def log(*args):
	if _gDebug>=1: apply(_log, args)

def logred(*args):
	if _gDebug>=1: 
		args = tuple (["[31m"] + list(args) + ["[0m"])
		apply(_log, args)

def debug(*args):
	if _gDebug>=2: apply(_log, args)


def debugfull():
	global _gDebug
	_gDebug = 2

def debugon():
	global _gDebug
	_gDebug = 1

def debugoff():
	global _gDebug
	_gDebug = 0



#----------------------------------------------------------------------
# testing...
def main(argv):
	# test rotate
	warn("Starting log test script...")
	l = Logger("logger", recyclePeriod=15, logPath="/u/chub/tmp", debug=0)
	for i in range(0,5):
		time.sleep(5)
		warn("Logging %d" % i)
	l = Logger("logger2", recyclePeriod=10, logPath="/u/chub/tmp", debug=1)
	for i in range(0,5):
		time.sleep(5)
		warn("Logging %d" % i)

if __name__ == "__main__":
	main (sys.argv)


	

		

	

		

		


