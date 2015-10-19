#! /usr/local/bin/python --

import serial

##
## Please pick a station type
##  (uncomment one of the following lines)

#kStationType = 'WMR968'
#kStationType = 'WM918'
kStationType = 'Davis'
#kStationType = 'Rainwise'

## ------------------------------------------

##
## Serial Communication Port
##
## Please pick a serial port type
##  (uncomment one of the following lines)
##

#kCommPort = serial.COM1
#kCommPort = serial.COM2
kCommPort = "/dev/ttyUSB0"
#kCommPort = "Choose"

## ------------------------------------------

##
## Weather Underground Connection Info
##
## Please change the userid and password to you
## Wunderground userid and password.
##
## To sign up for as a New Weather Station:
##
## http://www.wunderground.com/weatherstation/usersignup.asp
##

#kWundergroundUserID   = "userid"
kWundergroundPassword = "password"

## ------------------------------------------

kWeatherServer = 0         ## should we turn on the weather server?
#kWeatherServer = 1
#kWeatherServerPort = 9753  ## port for the weather server

## ------------------------------------------

## Update Interval (in minutes)
kWunderground_UpdateInterval = 15 * 60

## Update Interval (in seconds)
#kCSVFile = None
kCSVFile = "/dev/shm/current.csv"
kCSV_UpdateInterval = 15 * 60
kCSV_MaxLines = 20

## Update Interval (in seconds)
kShell_UpdateInterval = 86400
kUpdateInterval = 30

