#!/usr/bin/env python3

import argparse
import datetime
import sys
import contextlib
import os
import gzip
import re
from math import sin, cos, sqrt, atan2

##############################################################################

@contextlib.contextmanager
def smart_open(filename = None, mode = 'r'):
	
	if filename is None or filename == '-':
		if 'w' in mode:
			fh = sys.stdout
		else:
			fh = sys.stdin
	elif filename.endswith('.gz'):
		fh = gzip.open(filename, mode, 9)
	else:
		fh = open(filename, mode)
	
	try:
		yield fh
	finally:
		if fh is not sys.stdout and fh is not sys.stdin:
			fh.close()

##############################################################################

class PointClass:
	DateTime	= None
	Longitude	= None
	Latitude	= None
	Altitude	= None
	Speed		= None
	Bearing		= None
	Distance	= None
	
	x			= None
	y			= None
	
	def __repr__(self):
		return '%s [%10.6f %10.6f] (%.1f %.1f) %5.1fkm/h %5.1fdeg %.1fm' % (
			self.DateTime.isoformat() if self.DateTime is not None else 'None',
			self.Longitude, self.Latitude,
			self.x if self.x is not None else -1,
			self.y if self.y is not None else -1,
			self.Speed	if self.Speed	is not None else -1,
			self.Bearing  if self.Bearing  is not None else -1,
			self.Altitude if self.Altitude is not None else -1,
		)

##############################################################################

class GpsLogClass:
	Points = []
	
	def __init__(self):
		GpsLogClass.FuncTbl = {
			'nmea':			(self.Read_nmea,		self.Write_nmea),
			'gpx':			(self.Read_gpx,			self.Write_gpx),
			'kml':			(self.Read_kml,			self.Write_kml),
			'log':			(self.Read_vsd,			None),
			'vsd':			(self.Read_vsd,			None),
			'RaceChrono':	(self.Read_RaceChrono,	self.Write_RaceChrono),
			'dbg':			(None,					self.Write_debug),
		}
	
	##########################################################################
	
	_ToRad = 3.14159265358979 / 180
	
	# ヒュベニの公式
	_a = 6378137.0
	_b = 6356752.314140
	_e2 = (_a ** 2 - _b ** 2) / _a ** 2
	_Mnum = _a * (1 - _e2)
	
	def deg2rad(self, deg):
		return deg * self._ToRad
	
	def GenXY(self):
		if len(self.Points) == 0 or self.Points[0].x is not None:
			return
		
		self.Points[0].x = 0
		self.Points[0].y = 0
		
		for i in range(1, len(self.Points)):
			_dy = self.deg2rad(self.Points[i].Latitude - self.Points[i - 1].Latitude)
			_dx = self.deg2rad(self.Points[i].Longitude - self.Points[i - 1].Longitude)
			_My = self.deg2rad((self.Points[i].Latitude + self.Points[i - 1].Latitude) / 2)
			_W = sqrt(1 - self._e2 * sin(_My) ** 2)
			_M = self._Mnum / _W ** 3
			_N = self._a / _W
			
			self.Points[i].x = self.Points[i - 1].x + _dx * _N * cos(_My)
			self.Points[i].y = self.Points[i - 1].y + _dy * _M
	
	def Distance(self, p1, p2):
		return sqrt(
			(self.Points[p2].x - self.Points[p1].x) ** 2 +
			(self.Points[p2].y - self.Points[p1].y) ** 2
		)
	
	def Bearing(self, p1, p2):
		deg = atan2(self.Points[p2].x - self.Points[p1].x, self.Points[p2].y - self.Points[p1].y) / self._ToRad
		return deg if deg >= 0 else deg + 360
	
	##########################################################################
	# 欠落データ生成
	
	def GenSpeed(self, force = False):
		if len(self.Points) == 0 or (not force and self.Points[0].Speed is not None):
			return
		
		self.GenXY();
		self.Points[0].Speed = 0
		
		for i in range(1, len(self.Points)):
			self.Points[i].Speed = self.Distance(i - 1, i) / (
				self.Points[i].DateTime.timestamp() - self.Points[i - 1].DateTime.timestamp()
			) * (3600 / 1000)
	
	def GenBearing(self, force = False):
		if len(self.Points) == 0 or (not force and self.Points[0].Bearing is not None):
			return
		
		self.GenXY();
		
		for i in range(1, len(self.Points)):
			self.Points[i].Bearing = self.Bearing(i - 1, i)
		
		self.Points[0].Bearing = self.Points[1].Bearing
	
	def GenDistance(self, force = False):
		if len(self.Points) == 0 or (not force and self.Points[0].Distance is not None):
			return
		
		self.GenXY();
		self.Points[0].Distance = 0
		
		for i in range(1, len(self.Points)):
			self.Points[i].Distance = self.Points[i - 1].Distance + self.Distance(i - 1, i)
	
	def GenAltitude(self, force = False):
		if len(self.Points) == 0 or (not force and self.Points[0].Altitude is not None):
			return
		
		for i in range(len(self.Points)):
			self.Points[i].Altitude = 0	# 無いものは無い
	
	##########################################################################
	# reader / writer auto detect
	
	def GetFormat(self, file, format):
		if not format and file is not None and file != '-':
			(file2, ext) = os.path.splitext(file)
			if ext == '.gz':
				(file2, ext) = os.path.splitext(file2)
			
			if len(ext) >= 2:
				format = ext[1:].lower()
				
		if format in self.FuncTbl:
			return format
		
		raise Exception('Unknown format: %s format=%s' % (str(file), str(format)))
	
	def Read(self, file, format):
		format = self.GetFormat(file, format)
		
		if format not in self.FuncTbl or self.FuncTbl[format][0] is None:
			raise Exception('Format %s input not available: %s ' % (str(format), str(file)))
		
		self.FuncTbl[format][0](file)
	
	def Write(self, file, format):
		format = self.GetFormat(file, format)
		
		if self.FuncTbl[format][1] is None:
			raise Exception('Format %s output not available: %s ' % (str(format), str(file)))
		
		self.FuncTbl[format][1](file)
	
	##########################################################################
	# NMEA reader/writer
	
	#		HHMMSS	   lat		   lng			knot bearing  ddmmyy
	# 0	  1		  2 3		   4 5			6 7	  8	  9
	# $GPRMC,210624.000,A,3401.234567,N,13501.234567,E,19.738,249.05,010912,,,A*60
	#
	#		HHMMSS	 lat		 lng		   sat hdop alt
	# 0	  1		  2		 3 4		  5 6 7  8   9  10 11  12
	# $GPGGA,085120.307,3541.1493,N,13945.3994,E,1,08,1.0,6.9,M,35.9,M,,0000*5E
	
	def NmeaStr2LatLng(self, LatLngStr, Dir):
		LatLng = float(LatLngStr)
		LatLng = LatLng // 100 + (LatLng - LatLng // 100 * 100) / 60
		if Dir == 'W' or Dir == 'S':
			LatLng = -LatLng
		return LatLng
	
	def NmeaLatLng2Str(self, LatLng):
		return str(int(LatLng) * 100 + (LatLng - int(LatLng)) * 60)
	
	def NmeaGenChksum(self, Str):
		sum = ord('$')
		
		for c in Str:
			sum ^= ord(c)
		
		return '*%02X' % (sum,)
	
	def Read_nmea(self, FileName):
		with smart_open(FileName, 'rt') as FileIn:
			PrevTime = ''
			
			for Line in FileIn:
				if Line.startswith('$GPRMC') or Line.startswith('$GPGGA'):
					Param = Line.split(',')
					
					if PrevTime == Param[1]:
						Point = self.Points[len(self.Points) - 1]
					else:
						Point = PointClass()
						self.Points.append(Point)
					PrevTime = Param[1]
					
					if Line.startswith('$GPRMC'):
						
						Time	= float(Param[1])
						TimeUs	= int(Time * 1000 + 0.5) % 1000 * 1000
						Time	= int(Time)
						Date	= int(Param[9])
						Point.DateTime	= datetime.datetime(
							Date % 100 + 2000, Date // 100 % 100, Date // 10000,
							Time // 10000, Time // 100 % 100, Time % 100, TimeUs,
							tzinfo = datetime.timezone.utc
						)
						
						Point.Longitude	= self.NmeaStr2LatLng(Param[5], Param[6])
						Point.Latitude	= self.NmeaStr2LatLng(Param[3], Param[4])
						
						if len(Param[7]) > 0:
							Point.Speed = float(Param[7]) * 1.852
						if len(Param[8]) > 0:
							Point.Bearing = float(Param[8])
						
					else:
						if len(Param[9]) > 0:
							Point.Altitude = float(Param[9])
	
	def Write_nmea(self, FileName):
		with smart_open(FileName, 'wt') as FileOut:
			for Point in self.Points:
				Time = Point.DateTime.strftime('%H%M%S') + ('.%03d' % (Point.DateTime.microsecond // 1000,))
				Lat = self.NmeaLatLng2Str(Point.Latitude)  + ',N' if Point.Latitude  >= 0 else ',S'
				Lng = self.NmeaLatLng2Str(Point.Longitude) + ',E' if Point.Longitude >= 0 else ',W'
				
				s = '$GPRMC,%s,A,%s,%s,%s,%s,%s,,,A' % (
					Time, Lat, Lng,
					str(Point.Speed / 1.852) if Point.Speed is not None else '',
					str(Point.Bearing) if Point.Bearing is not None else '',
					Point.DateTime.strftime('%d%m%y')
				)
				FileOut.write(s + self.NmeaGenChksum(s) + '\n')
				
				s = '$GPGGA,%s,%s,%s,1,08,1.0,%s,M,,,,' % (
					Time, Lat, Lng, str(Point.Altitude)
				)
				FileOut.write(s + self.NmeaGenChksum(s) + '\n')
	
	##########################################################################
	# GPX reader/writer
	
	def Read_gpx(self, FileName):
		with smart_open(FileName, 'rt') as FileIn:
			for match in re.finditer('<trkpt.*?</trkpt>', FileIn.read(), flags = re.DOTALL):
				Point = PointClass()
				
				str = match.group(0)
				
				m = re.search(r'<time>\s*(\S+?)\s*</', str)
				if not m:
					continue
				Point.DateTime = datetime.datetime.fromisoformat(m.group(1).replace('Z', '+00:00'))
				
				m = re.search(r'lat="(.*?)"', str)
				if not m:
					continue
				Point.Latitude = float(m.group(1))
				
				m = re.search(r'lon="(.*?)"', str)
				if not m:
					continue
				Point.Longitude = float(m.group(1))
				
				m = re.search(r'<ele>\s*(\S+?)\s*</', str)
				if m:
					Point.Altitude = float(m.group(1))
				
				m = re.search(r'<speed>\s*(\S+?)\s*</', str)
				if m:
					Point.Speed = float(m.group(1)) * 3.6
				
				m = re.search(r'<course>\s*(\S+?)\s*</', str)
				if m:
					Point.Bearing = float(m.group(1))
				
				self.Points.append(Point)
	
	def Write_gpx(self, FileName):
		with smart_open(FileName, 'wt') as FileOut:
			
			FileOut.write(
				'<?xml version="1.0"?><gpx version="1.0" creator="GPSLogger - http://gpslogger.mendhak.com/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.topografix.com/GPX/1/0" xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd"><time>%s</time><bounds /><trk><trkseg>\n' % (
					self.Points[0].DateTime.isoformat()
				)
			)
			
			self.GenSpeed()
			self.GenAltitude()
			self.GenBearing()
			
			for Point in self.Points:
				FileOut.write(
					'<trkpt lat="%s" lon="%s"><ele>%s</ele><course>%s</course><speed>%s</speed><time>%s</time></trkpt>\n' % (
						str(Point.Latitude), str(Point.Longitude), str(Point.Altitude),
						str(Point.Bearing), str(Point.Speed / 3.6), Point.DateTime.isoformat()
					)
				)
			
			FileOut.write('</trkseg></trk></gpx>\n')
	
	##########################################################################
	# KML reader/writer
	
	def Read_kml(self, FileName):
		with smart_open(FileName, 'rt') as FileIn:
			for match in re.finditer('<Placemark.*?</Placemark>', FileIn.read(), flags = re.DOTALL):
				Point = PointClass()
				
				str = match.group(0)
				
				m = re.search(r'<when>\s*(\S+?)\s*</', str)
				if not m:
					continue
				Point.DateTime = datetime.datetime.fromisoformat(m.group(1).replace('Z', '+00:00'))
				
				m = re.search(r'<coordinates>\s*([\d\.\-]+),([\d\.\-]+)\s*</', str)
				if not m:
					continue
				Point.Longitude = float(m.group(1))
				Point.Latitude  = float(m.group(2))
				
				self.Points.append(Point)
	
	def Write_kml(self, FileName):
		with smart_open(FileName, 'wt') as FileOut:
			
			self.GenSpeed()
			self.GenAltitude()
			self.GenBearing()
			self.GenDistance()
			
			FileOut.write('''\
<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
    xmlns:gx="http://www.google.com/kml/ext/2.2">
  <Document>
    <name>GPS device</name>
    <snippet>Created {now}</snippet>
    <LookAt>
      <gx:TimeSpan>
        <begin>{start}</begin>
        <end>{end}</end>
      </gx:TimeSpan>
      <longitude>kml</longitude>
      <latitude>{lat}</latitude>
      <range>1300.000000</range>
    </LookAt>
<!-- Normal track style -->
    <Style id="track_n">
      <IconStyle>
        <scale>.5</scale>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href>
        </Icon>
      </IconStyle>
      <LabelStyle>
        <scale>0</scale>
      </LabelStyle>
    </Style>
<!-- Highlighted track style -->
    <Style id="track_h">
      <IconStyle>
        <scale>1.2</scale>
        <Icon>
          <href>http://earth.google.com/images/kml-icons/track-directional/track-none.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <StyleMap id="track">
      <Pair>
        <key>normal</key>
        <styleUrl>#track_n</styleUrl>
      </Pair>
      <Pair>
        <key>highlight</key>
        <styleUrl>#track_h</styleUrl>
      </Pair>
    </StyleMap>
<!-- Normal waypoint style -->
    <Style id="waypoint_n">
      <IconStyle>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/pal4/icon61.png</href>
        </Icon>
      </IconStyle>
    </Style>
<!-- Highlighted waypoint style -->
    <Style id="waypoint_h">
      <IconStyle>
        <scale>1.2</scale>
        <Icon>
          <href>http://maps.google.com/mapfiles/kml/pal4/icon61.png</href>
        </Icon>
      </IconStyle>
    </Style>
    <StyleMap id="waypoint">
      <Pair>
        <key>normal</key>
        <styleUrl>#waypoint_n</styleUrl>
      </Pair>
      <Pair>
        <key>highlight</key>
        <styleUrl>#waypoint_h</styleUrl>
      </Pair>
    </StyleMap>
    <Style id="lineStyle">
      <LineStyle>
        <color>FFFFFF00</color>
        <width>1</width>
      </LineStyle>
    </Style>
    <Folder>
      <name>Tracks</name>
      <Folder>
        <snippet/>
        <description>
          <![CDATA[<table>
            <tr><td><b>Distance</b>{dist}m</td></tr>
            <tr><td><b>Start Time</b>{start}</td></tr>
            <tr><td><b>End Time</b>{end}</td></tr>
          </table>]]>
        </description>
        <TimeSpan>
          <begin>{start}</begin>
          <end>{end}</end>
        </TimeSpan>
        <Folder>
          <name>Points</name>
'''                    .format(
                        now        = str(datetime.datetime.now()),
                        start    = self.Points[0].DateTime.isoformat(),
                        end        = self.Points[len(self.Points) - 1].DateTime.isoformat(),
                        lat        = str(self.Points[0].Latitude),
                        lng        = str(self.Points[0].Longitude),
                        dist    = '%.1f' % (self.Points[len(self.Points) - 1].Distance),
                    )
                )
            
            for Point in self.Points:
                FileOut.write('''\
          <Placemark>
            <snippet/>
            <description><![CDATA[
              <table>
                <tr><td>Longitude: {lng}</td></tr>
                <tr><td>Latitude: {lat}</td></tr>
                <tr><td>Speed: {speed}km/h</td></tr>
                <tr><td>Altitude: {alt}m</td></tr>
                <tr><td>Heading: {dir}</td></tr>
                <tr><td>Time: {time}</td></tr>
              </table>
            ]]></description>
            <LookAt>
              <longitude>{lng}</longitude>
              <latitude>{lat}</latitude>
              <tilt>66</tilt>
            </LookAt>
            <TimeStamp><when>{time}</when></TimeStamp>
            <styleUrl>#track</styleUrl>
            <Point>
              <coordinates>{lng},{lat}</coordinates>
            </Point>
          </Placemark>
'''					.format(
						time	= Point.DateTime.isoformat(),
						lat		= '%.8f' % (Point.Latitude,),
						lng		= '%.8f' % (Point.Longitude,),
						speed	= '%.1f' % (Point.Speed,),
						alt		= '%.1f' % (Point.Altitude,),
						dir		= '%.1f' % (Point.Bearing,),
					)
				)
			
			FileOut.write('''\
        </Folder>
        <Placemark>
          <name>Path</name>
          <styleUrl>#lineStyle</styleUrl>
          <LineString>
            <tessellate>1</tessellate>
            <coordinates>
''')
			
			for Point in self.Points:
				FileOut.write('			  %.8f,%.8f\n' % (Point.Longitude, Point.Latitude))
			
			FileOut.write('''\
            </coordinates>
          </LineString>
        </Placemark>
      </Folder>
    </Folder>
  </Document>
</kml>
''')
	
	##########################################################################
	# RaceChrono reader/writer
	# 1: ULONG epoch 時刻 [ms]
	# 2: ULONG 走行距離 [1/1000m]
	# 3: int latitude, int longitude [1/6000000度]
	# 4: UINT 速度 [1/277.7792km/h, キリがいいのに近いのは 1/512knot?]
	# 5: 高度 [1/1000m]
	# 6: UINT bearing [1/1000度]
	# 30002: 捕捉衛生数
	# 30003: 位置特定品質 ($GPGGA)
	# 30004: DOP 座標精度 [*1/1000]
	# 30005: DOP 座標精度 [*1/1000], -128:データなし
	# すべてリトルエンディアン
	
	def Read_RaceChrono(self, DirName):
		if DirName == '-':
			raise Exception("RaceChrono reader can't input from stdin")
		
		with open(DirName + '/channel_1_100_0_1_1', 'rb') as fhTime:
			with open(DirName + '/channel_1_100_0_2_1', 'rb') as fhDistance:
				with open(DirName + '/channel_1_100_0_3_1', 'rb') as fhLatLng:
					with open(DirName + '/channel_1_100_0_4_0', 'rb') as fhSpeed:
						with open(DirName + '/channel_1_100_0_5_0', 'rb') as fhAlt:
							with open(DirName + '/channel_1_100_0_6_0', 'rb') as fhDir:
								while True:
									Point = PointClass()
									
									data = fhTime.read(8)
									if len(data) < 8:
										break
									Point.DateTime = datetime.datetime.utcfromtimestamp(int.from_bytes(data, 'little') / 1000)
									
									data = fhDistance.read(8)
									if len(data) < 8:
										break
									Point.Distance = int.from_bytes(data, 'little') / 1000
									
									data = fhLatLng.read(8)
									if len(data) < 8:
										break
									Point.Longitude = int.from_bytes(data[4:8], 'little', signed = True) / 6000000
									Point.Latitude  = int.from_bytes(data[0:4], 'little', signed = True) / 6000000
									
									data = fhSpeed.read(4)
									if len(data) < 4:
										break
									Point.Speed = int.from_bytes(data, 'little') / 277.7792
									
									data = fhAlt.read(4)
									if len(data) < 4:
										break
									Point.Altitude = int.from_bytes(data, 'little', signed = True) / 1000
									
									data = fhDir.read(4)
									if len(data) < 4:
										break
									Point.Bearing = int.from_bytes(data, 'little') / 1000
									
									self.Points.append(Point)
	
	def Write_RaceChrono(self, DirName):
		if DirName == '-':
			raise Exception("RaceChrono writer can't output to stdout")
		
		# dir 作成
		os.makedirs(DirName, exist_ok=True)
		
		with open(DirName + '/channel_1_100_0_1_1', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.DateTime.timestamp() * 1000).to_bytes(8, 'little'))
		
		self.GenDistance()
		with open(DirName + '/channel_1_100_0_2_1', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.Distance * 1000).to_bytes(8, 'little'))
		
		with open(DirName + '/channel_1_100_0_3_1', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.Latitude  * 6000000).to_bytes(4, 'little', signed = True))
				FileOut.write(int(Point.Longitude * 6000000).to_bytes(4, 'little', signed = True))
		
		self.GenSpeed()
		with open(DirName + '/channel_1_100_0_4_0', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.Speed * 277.7792).to_bytes(4, 'little'))
		
		self.GenAltitude()
		with open(DirName + '/channel_1_100_0_5_0', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.Altitude * 1000).to_bytes(4, 'little', signed = True))
		
		self.GenBearing()
		with open(DirName + '/channel_1_100_0_6_0', 'wb') as FileOut:
			for Point in self.Points:
				FileOut.write(int(Point.Bearing * 1000).to_bytes(4, 'little', signed = True))
	
	##########################################################################
	# VSD reader
	# 0		1							2			3			4		5
	# GPS	2019-01-04T04:34:39.200Z	136.12345	35.12345	92.600	0.037
	def Read_vsd(self, FileName):
		with smart_open(FileName, 'rt') as FileIn:
			PrevTime = ''
			
			for Line in FileIn:
				if Line.startswith('GPS'):
					Param = Line.split('\t')
					
					if PrevTime == Param[1]:
						continue
					PrevTime = Param[1]
					
					Point = PointClass()
					self.Points.append(Point)
					
					Point.DateTime	= datetime.datetime.fromisoformat(Param[1].replace('Z', '+00:00'))
					Point.Longitude	= float(Param[2])
					Point.Latitude	= float(Param[3])
					Point.Altitude	= float(Param[4])
					Point.Speed		= float(Param[5])
	
	##########################################################################
	# Points dumper
	def Write_debug(self, FileName):
		with smart_open(FileName, 'wt') as FileOut:
			FileOut.write(str(self.Points).replace(',', '\n'))
	
	##########################################################################
	# smart reduce point
	def DistanceLine2Pix(self, p1, p2, p3):
		x1 = self.Points[p1].x
		y1 = self.Points[p1].y
		px = self.Points[p2].x
		py = self.Points[p2].y
		x2 = self.Points[p3].x
		y2 = self.Points[p3].y
		
		a = x2 - x1
		b = y2 - y1
		a2 = a * a
		b2 = b * b
		r2 = a2 + b2
		tt = -(a * (x1 - px) + b * (y1 - py))
		if tt < 0:
			return (x1 - px) * (x1 - px) + (y1 - py) * (y1 - py)
		if tt > r2:
			return (x2 - px) * (x2 - px) + (y2 - py) * (y2 - py)
		
		f1 = a * (y1 - py) - b * (x1 - px)
		return f1 * f1 / r2
	
	def ReduceSmart(self):
		self.GenXY()
		
		st = 0
		while st < len(self.Points) - 2:
			ed = st + 2
			del_ok = -1
			
			for ed in range(st + 2, len(self.Points)):
				md = (st + ed) // 2
				
				dist = self.Distance(st, ed)
				if dist < 5 or self.DistanceLine2Pix(st, md, ed) < 5:
					del_ok = ed
				else:
					break
			
			if del_ok > 0:
				for i in range(st, ed):
					self.Points[i].DateTime = None
				st = del_ok
			else:
				st += 1
		
		PointsNew = []
		for Point in self.Points:
			if Point.DateTime:
				PointsNew.append(Point)
		
		print("%d/%d" % (len(PointsNew), len(self.Points),))
		self.Points = PointsNew
	
##############################################################################
# process all file

def Convert(Arg):
	if len(Arg.input_file) == 0:
		Arg.input_file.append('-')
	
	if Arg.output_file:
		Arg.cat = True
	elif not Arg.output_format:
		raise Exception('Output format not specified')
	
	if not hasattr(Arg, 'cat'):
		Arg.cat = False
	
	# 全入力を 1出力にまとめる
	if Arg.cat:
		GpsLog = GpsLogClass()
	
	for input_file in Arg.input_file:
		if not Arg.cat:
			GpsLog = GpsLogClass()
			output_file = input_file
			if output_file.endswith('.gz'):
				output_file = output_file[:-3]
			
			output_file = os.path.splitext(output_file)[0]
			if Arg.output_format != 'RaceChrono':
				output_file += '.' + Arg.output_format
		
		GpsLog.Read(input_file, Arg.input_format)
		
		if not Arg.cat:
			GpsLog.Write(output_file, Arg.output_format)
	
	if Arg.cat:
		GpsLog.Write(Arg.output_file, Arg.output_format)

##############################################################################
# main
if __name__ == '__main__':
	
	ArgParser = argparse.ArgumentParser(description = 'GPS log converter')
	ArgParser.add_argument('input_file', nargs = '*', help = 'input files')
	ArgParser.add_argument('-I', metavar = 'input_format', dest = 'input_format', help = 'input format')
	ArgParser.add_argument('-O', metavar = 'output_format', dest = 'output_format', help = 'output format')
	ArgParser.add_argument('-o', metavar = 'output_file', dest = 'output_file', help = 'output file')
	Arg = ArgParser.parse_args()
	
	Convert(Arg)
