#! /usr/local/bin/python --

"""
usage: %(progname)s [args]
"""


import os, sys, string, time, getopt
from log import *


def DewCalc(rh, temp):
	import math
	if rh<1 or rh>100 or temp<-100 or temp>200:
		return 100

	if rh > 100: return temp

	temp= (5.0/9.0)*(temp-32.0)
	ews= rh*0.01*math.exp((17.502*temp)/(240.9+temp))
	num= 240.9*(math.log(ews))
	den= 17.5-(math.log(ews))
	dp= num/den

	if 1:
		dp = (9.0/5.0)*dp+32

	return dp

def Celsius2Fahrenheit(temp):
	return (temp * 9. / 5.) + 32

def Fahrenheit2Celsius(temp):
	return (temp - 32) * 5. / 9.

def Millibars2Inches(pressure):
	return pressure * 0.02953

def Inches2Millibars(pressure):
	return pressure / 0.02953

def MetersPerSecond2MilesPerHour(mps):
	return mps * 2.23693 

def MilesPerHour2MetersPerSecond(mph):
	return mph / 2.23693 

## ----------------------------------------------

BCDError = "BCDError"

def toBCD(n):
	if n < 0 or n > 99: return 0

	n1 = n / 10
	n2 = n % 10

	m = n1 << 4 | n2
	return m

def fromBCD(n):
	n1 = n & 0x0F
	n2 = n >> 4
	return n2 * 10 + n1



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
