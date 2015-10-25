from Tools.Directories import resolveFilename, SCOPE_CONFIG
from . import *
import thread
class Lamedb:
	def __init__(self):
		self.readcnt = 0
		self.database = {}
		self.databaseState=0
		thread.start_new_thread(self._initDatabase,(None,))
#		self._initDatabase(None,)
		
	def _initDatabase(self,dummy):
		print_gr ("Lamedb._initDatabase started")
		self.database.clear()
		self.databaseState=0
		print_gr ("phase1: translateTransponders")
		self.translateTransponders(self.getTransponders(self.readLamedb()))
		print_gr ("phase2:t ranslateServices")
		self.translateServices(self.getServices(self.readLamedb()))
		print_gr ("Lamedb._initDatabase finished")

	def readLamedb(self):

		f = file((resolveFilename(SCOPE_CONFIG) + "/lamedb"),"r")
#		f = file("/etc/enigma2/lamedb","r")
		lamedb = f.readlines()
		f.close()
		if lamedb[0].find("/3/") != -1:
			self.version = 3
		elif lamedb[0].find("/4/") != -1:
			self.version = 4
		else:
			print_rd ("unknown leame version: ",lamedb[0])
			return
		print_gr ("import lamedb version %d" % self.version)
		return lamedb

	def writeLamedb(self,version = 4):
		if version <> 4:
			print_ye ("only version 4 yet")
			return
		puffer = []
		puffer.append("eDVB services /4/\n")
		puffer.append("transponders\n")
		for tp in self.database:
			tp = self.database[tp]
			puffer.append(("%s:%s:%s\n")%(tp["namespace"],tp["tsid"],tp["onid"]))
			if tp["namespace"][:4].lower()=="ffff":
				puffer.append(("\tc %s:%s:%s:%s:%s:%s\n")%(tp["frequency"],tp["symbol_rate"],tp["inversion"],tp["modulation"],tp["fec_inner"],tp["flags"]))
			elif tp["namespace"][:4].lower()=="eeee":
				puffer.append(("\tt %s:%s:%s:%s:%s:%s:%s:%s:%s:%s\n")%(tp["frequency"],tp["bandwidth"],tp["code_rate_HP"],tp["code_rate_LP"],tp["modulation"],tp["transmission_mode"],tp["guard_interval"],tp["hierarchy"],tp["inversion"],tp["flags"]))
			else:
				sys = tp.get("system",None)
				if sys is None or sys == "0":
					puffer.append(("\ts %s:%s:%s:%s:%s:%s:%s\n")%(tp["frequency"],tp["symbol_rate"],tp["polarization"],tp["fec_inner"],tp["position"],tp["inversion"],tp["flags"]))
				else:
					puffer.append(("\ts %s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s\n")%(tp["frequency"],tp["symbol_rate"],tp["polarization"],tp["fec_inner"],tp["position"],tp["inversion"],tp["flags"],tp["system"],tp["modulation"],tp["rolloff"],tp["pilot"]))
			puffer.append("/\n")	
		puffer.append("end\n")
		puffer.append("services\n")
		for tp in self.database:
			for service in self.database[tp]["services"]:
				service = self.database[tp]["services"][service]
				puffer.append(("%s:%s:%s:%s:%s:%s\n")%(service["sid"],service["namespace"],service["tsid"],service["onid"],service["type"],service["number"]))
				puffer.append(("%s\n")%service["name"])
				tmp = ""
				cacheIDs = service.get("cacheIDs",None)
				if cacheIDs is not None:
					for cacheID in cacheIDs:
						tmp += ",c:" + cacheID
				caIDs = service.get("caIDs",None)
				if caIDs is not None:
					for caID in caIDs:
						tmp += ",C:" + caID
				flags = service.get("flags",None)
				if flags is not None and int(flags,16)!=0:
					tmp += ",f:" + flags
				puffer.append(("p:%s%s\n")%(service["provider"],tmp))
		puffer.append("end\n")
		puffer.append("Have a lot of girls\n")
		f = file("/etc/enigma2/lamedb","w")
		f.writelines(puffer)
		f.close()

	def writeM3U(self):
		puffer = []
		puffer.append("#EXTM3U\n")
		for tp in self.database:
			for service in self.database[tp]["services"]:
				service = self.database[tp]["services"][service]
				puffer.append("#EXTINF:-1,%s\n" % service["name"].replace(' ','_'))
	#FIXME src soll irgendwie DiSEqC-CMD sein ???
	#FIXME polarisation ist hier noch als Zahlenwert, das muss aber v oder h sein
	#FIXME Frequenz auf MHz gerundet
	#FIXME Sysmbolrate auf kHz gerundet
				puffer.append("http://<?=StatusIP?>?src=%s&freq=%s&sr=%s&pol=%s" %(1, tp["frequency"], tp["symbol_rate"], tp["polarization"]) )

		f = file("/tmp/astra_all_services.m3u","w")
		f.writelines(puffer)
		f.close()
		
	def getServices(self, lamedb):
		print_gr ("Lamedb.getServices started")
		services = []
		collect = False
		state = 0
		lamdb_len = len(lamedb)
		skip_processed_lines = 0
		if lamedb is not  None:
			for x in xrange(lamdb_len - 2):
				if lamedb[x] == "services\n":
					collect = True
					continue
				if lamedb[x] == "end\n":
					collect = False
					continue
				if collect:
					if skip_processed_lines:
						skip_processed_lines -= 1
						continue
					if  lamedb[x].find(",") == -1 and lamedb[x].find(":") != -1:
						tmp = lamedb[x].split(":")
						if len(tmp) >= 4:
#							print_cy("ok --> %s" %lamedb[x]) # #adenin_debug
							if tmp[1]+tmp[2]+tmp[3] in self.database:
								tmp = lamedb[x+2].split(",")
								for key in tmp:
									key = key.split(":")
#									if len(key)==2 and key[0].strip() in ("c","C","f","p",):
									if len(key)==2:
										continue
									else:
										print_ye ("key count != 2 => %s %s" %(lamedb[x], key))
										break
								else:
									services.append((lamedb[x],lamedb[x+1],lamedb[x+2],))
									skip_processed_lines = 2
#									self.translateService((lamedb[x],lamedb[x+1],lamedb[x+2],))
						else:
							print_rd("we excepte last four colon separeted parts --> %s" %lamedb[x])
							pass
					else:
						print_rd ("unknown format (maybe?)--> %s" %lamedb[x])
						pass
				else:
#					print_ye("Stuff that is not in the service section --> %s" %lamedb[x])
					pass
		else:
			print_ye ("lamedb ist empty, no services found")
			pass
		print_gr ("Lamedb.getServices finished")
		return services
	
	
	def translateService(self, serviceData):
		t1 = ["sid","namespace","tsid","onid","type","number"]
		if serviceData is None:
			return
		service = {}
		service_update = service.update
		service_get = service.get
		tp_data = serviceData[0].strip().lower().split(":")
		if len(tp_data) > len(t1):
			print "falsche Anzahl Parameter (6 erwartet) in ",serviceData[0]
			return
		for y in xrange(len(t1)):
			service_update({t1[y]:tp_data[y]})

		name = serviceData[1].strip().replace('\xc2\x86', '').replace('\xc2\x87', '').replace('\xc3\x82', '')
		service_update({"name":name})
		provider_data = serviceData[2].strip().split(",")
		for y in provider_data:
			raw = y.split(":")
#			if len(raw)==2 and raw[0].strip() in ("c","C","f","p",):
			if raw[0]=="p":
				service["provider"] = raw[1].strip().replace('\xc2\x86', '').replace('\xc2\x87', '').replace('\xc3\x82', '')
			elif raw[0]=="c":
				cacheIDs = service_get("cacheIDs",None)
				if cacheIDs is None:
					service["cacheIDs"] = [raw[1].strip().lower(),]
				else:
					cacheIDs.append(raw[1].strip().lower())
			elif raw[0]=="C":
				caIDs = service_get("caIDs",None)
				if caIDs is None:
					service["caIDs"] = [raw[1].strip().lower(),]
				else:
					caIDs.append(raw[1].strip().lower())
			elif raw[0]=="f":
				service["flags"] = raw[1].strip().lower()
			else:
				print "unbekanter Parameter:",raw[0]
				print "in:",y
#			else:
#				print "hmm, da stimmt was mit den Daten nicht:",raw
#				break
		else:
			uniqueTransponder = service["namespace"]+service["tsid"]+service["onid"]
			uniqueService = uniqueTransponder + service["sid"]
			if (int(service_get("flags","0"),16) & dxNoDVB):
				for cacheID in service_get("cacheIDs",[]):
					uniqueService += cacheID
			service["usk"] = uniqueService
			self.database[uniqueTransponder]["services"][uniqueService] = service
			self.readcnt += 1
			self.databaseState=3
	
	def translateServices(self, services):
		if services is None:
			return
		for x in services:
			self.translateService(x)
		else:
			self.databaseState=4
	

	def getTransponders(self, lamedb):
		if lamedb is None:
			return
		collect = False
		state = 0
		transponders = []
		tp = []
		for x in lamedb:
			if x == "transponders\n":
				collect = True
				continue
			if x == "end\n":
				collect = False
				continue
			y = x.strip().lower().split(":")
			if collect:
				if y[0] == "/":
					transponders.append(tp)
					tp = []
				else:
					tp.append(y)
		return transponders

	def translateTransponders(self, transponders):
		t1 = ["namespace","tsid","onid"]
		t2_sv3 = ["frequency",
			"symbol_rate",
			"polarization",
			"fec_inner",
			"position",
			"inversion",
			"system",
			"modulation",
			"rolloff",
			"pilot",
			]
		t2_sv4 = ["frequency",
			"symbol_rate",
			"polarization",
			"fec_inner",
			"position",
			"inversion",
			"flags",
			"system",
			"modulation",
			"rolloff",
			"pilot"
			]
		t2_t = ["frequency",
			"bandwidth",
			"code_rate_HP",
			"code_rate_LP",
			"modulation",
			"transmission_mode",
			"guard_interval",
			"hierarchy",
			"inversion",
			"flags",
			]
		t2_c = ["frequency",
			"symbol_rate",
			"inversion",
			"modulation",
			"fec_inner",
			"flags",
			]

		if transponders is None:
			return
		for x in transponders:
			if len(x[0]) > len(t1):
				print "zu viele Parameter (t1) in ",x[0]
				continue
			freq = x[1][0].split()
			if len(freq) != 2:
				print "zwei Parameter erwartet in ",freq
				continue
			tp = {"services":[]}
			x[1][0] = freq[1]
			if freq[0] == "s":
				if ((self.version == 3) and len(x[1]) > len(t2_sv3)) or ((self.version == 4) and len(x[1]) > len(t2_sv4)):
					print "zu viele Parameter (t2) in ",x[1]
					continue
				for y in xrange(len(x[0])):
					tp.update({t1[y]:x[0][y]})
				for y in xrange(len(x[1])):
					if self.version == 3:	
						tp.update({t2_sv3[y]:x[1][y]})
					elif self.version == 4:
						tp.update({t2_sv4[y]:x[1][y]})
				pos = int(tp.get("namespace"),16) >>16
				if pos > 1799:
					pos -= 3600
				if pos != int(tp.get("position")):
					print "Namespace %s und Position %s sind  nicht identisch"% (tp.get("namespace"), tp.get("position"))
					continue
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]] = tp
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]]["services"] = {}
				self.databaseState=1
			elif freq[0] == "c":
				if len(x[1]) > len(t2_c):
					print "zu viele Parameter (t2) in ",x[1]
					continue
				for y in xrange(len(x[0])):
					tp.update({t1[y]:x[0][y]})
				for y in xrange(len(x[1])):
					tp.update({t2_c[y]:x[1][y]})
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]] = tp
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]]["services"] = {}
				self.databaseState=1
			elif freq[0] == "t":
				if len(x[1]) > len(t2_t):
					print "zu viele Parameter (t2) in ",x[1]
					continue
				for y in xrange(len(x[0])):
					tp.update({t1[y]:x[0][y]})
				for y in xrange(len(x[1])):
					tp.update({t2_t[y]:x[1][y]})
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]] = tp
				self.database[tp["namespace"]+tp["tsid"]+tp["onid"]]["services"] = {}
				self.databaseState=1
		else:
			self.databaseState=2

dxNoSDT=1    	# don't get SDT
dxDontshow=2
dxNoDVB=4		# dont use PMT for this service ( use cached pids )
dxHoldName=8
dxNewFound=64

#typ der cacheIDs
VIDEO_PID = 0
AUDIO_PID = 1		#wenn aPid, dann darf kein ac3Pid vorhanden sein
TXT_PID = 2
PCR_PID = 3
AC3_PID = 4		#wenn ac3Pid, dann darf kein aPid vorhanden sein
VIDEOTYPE = 5		# 0=MPEG2, 1=MPEG4_H264, 2=MPEG1, 3=MPEG4_Part2, 4=VC1, 5=VC1_SM
AUDIOCHANNEL = 6	#Audiochannel
AC3_DELAY = 7
PCM_DELAY = 8
SUBTITLE_PID = 9