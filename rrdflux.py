#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys,getopt
import re
import os
import rrdtool
import xml.etree.ElementTree as ET
import pprint
from influxdb import InfluxDBClient


def main(argv):

   RRD_MIN_RES=60

   update=False
   dump=False
   fname=""
   host="localhost"
   port="8086"
   db=""
   key=""
   user=""
   password=""
   device=""
   timens=1
   start='-1y'

   def help():
      print('Usage: rddflux.py [-u|-m] -f <RRD FILE> [-H <INFLUXDB HOST>] [-p <INFLUXDB PORT>] -d DATABASE [-U user] [-P password] [-k KEY] -D device [-h] ')
      print('Updates or dumps passed RRD File to selected InfluxDB database')
      print('	-h, --help		Display help and exit')
      print('	-u, --update		Only update database with last value')
      print('	-m, --dump		Dump full RRD to database')
      print('	-f, --file		RRD file to dump')
      print('	-H, --host		Optional. Name or IP of InfluxDB server. Default localhost.')
      print('	-p, --port		Optional. InfluxDB server port. Default 8086.')
      print('	-d, --database		Database name where to store data.')
      print('	-U, --user		Optional. Database user.')
      print('	-P, --password		Optional. Database password.')
      print('	-k, --key		Optional. Key used to store data values. Taken from RRD file\'s name if not specified.')
      print('	-D, --device		Device the RRD metrics are related with.')
      print('	-t, --timens		Multiply RRD timeestamps to ns for influxdb')
      print('	-s, --start		RRD Start value, default -1y')
   try:
       opts, args = getopt.getopt(argv,"htumf:H:p:d:U:P:k:D:s:",["help=","timens","update=","dump=","file=","host=","port=","database=","user=","password=","key=","device=","start="])
   except getopt.GetoptError:
      help()
      sys.exit(2)

   for opt, arg in opts:
      if opt == '-h':
         help()
         sys.exit()
      elif opt in ("-u", "--update"):
         update = True
      elif opt in ("-m", "--dump"):
         dump = True
      elif opt in ("-f", "--file"):
         fname = arg
      elif opt in ("-H", "--host"):
         host = arg
      elif opt in ("-p", "--port"):
         port = arg
      elif opt in ("-d", "--database"):
         db = arg
      elif opt in ("-U", "--user"):
         user = arg
      elif opt in ("-P", "--password"):
         password = arg
      elif opt in ("-k", "--key"):
         key = arg
      elif opt in ("-D", "--device"):
         device = arg
      elif opt in ("-t", "--timens"):
         timens = 1000 * 1000 * 1000
      elif opt in ("-s", "--start"):
         start = arg

   if device == "" or fname == "" or db == "" or (update == False and dump == False) or (update == True and dump == True):
      print("ERROR: Missing or duplicated parameters.")
      help()
      sys.exit(2)

   client = InfluxDBClient(host, port, user, password, db)
   client.query("create database "+db+";") # Create database if it not exists
   
   if key == "":
      key = re.sub('\.rrd$','',os.path.split(fname)[1])
  
   if update == True:
      # We save the last two records of the rrd tool to avoid missing data 
      lastvalue = rrdtool.fetch(fname,"AVERAGE",'-s', str(rrdtool.last(fname)-2*RRD_MIN_RES),
                                                '-e', str(rrdtool.last(fname)-RRD_MIN_RES),'-r', str(RRD_MIN_RES))
      unixts=lastvalue[0][1]
      val=lastvalue[2][0][0]
      json_body = [
         {
            "measurement": device,
            "time": unixts * timens,
            "fields": {
                key: val,
            }
         }
      ]
      client.write_points(json_body)

      unixts=lastvalue[0][1]-RRD_MIN_RES
      val=lastvalue[2][0][0]
      json_body = [
         {
            "measurement": device,
            "time": unixts * timens,
            "fields": {
                key: val,
            }
         }
      ]
      client.write_points(json_body)


   if dump == True:
      allvalues = rrdtool.fetch(
         fname,
         "AVERAGE",
         '-s', start,
         '-e', str(rrdtool.last(fname)-RRD_MIN_RES),
         '-r', str(RRD_MIN_RES))
      i=0
      while i < len(allvalues[2]):
         json_body = []
         if i + 1024 < len(allvalues[2]):
             loop = 1024
         else:
             loop = len(allvalues[2]) - i
         for z in range(0, loop):
             val=allvalues[2][i][0]
             if val:
                 unixts=allvalues[0][0]+(i+1)*RRD_MIN_RES
                 json_body.append(
                    {
                       "measurement": device,
                       "time": unixts * timens,
                       "fields": {
                           key: val,
                       }
                    }
                 )
             i=i+1
         client.write_points(json_body)
         print("done {} of {}".format(i, len(allvalues[2])))

if __name__ == "__main__":
   main(sys.argv[1:])


