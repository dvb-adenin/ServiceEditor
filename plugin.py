# -*- coding: iso-8859-1 -*-
# Tabsize 4

#from __future__ import absolute_import
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config, ConfigBoolean, ConfigFloat, ConfigInteger, ConfigSelection, ConfigText, ConfigYesNo, getConfigListEntry, KEY_NUMBERS, KEY_ASCII, getKeyNumber
from Components.ConfigList import ConfigListScreen
from Components.FileList import FileList
from Components.GUIComponent import GUIComponent
from Components.HTMLComponent import HTMLComponent
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.NimManager import nimmanager, getConfigSatlist
from Components.Pixmap import Pixmap
from enigma import eDVBDB, eListbox, gFont, eListboxPythonMultiContent, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, eRect, eTimer

from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from time import strftime, time, localtime, mktime
from Tools.Directories import resolveFilename, SCOPE_SKIN_IMAGE
from Tools.LoadPixmap import LoadPixmap

from . import _
from .Transponder import Transponder
from .ConfigHexNumber import ConfigHexNumber
from .Lamedb import Lamedb, VIDEO_PID,AUDIO_PID,TXT_PID,PCR_PID,AC3_PID,VIDEOTYPE,AUDIOCHANNEL,AC3_DELAY,PCM_DELAY,SUBTITLE_PID, \
	dxNoSDT,dxDontshow,dxNoDVB,dxHoldName,dxNewFound

import os
import thread
import time

class ServiceList(MenuList):
	def __init__(self):
		MenuList.__init__(self, list = [], content = eListboxPythonMultiContent)
		self.l.setItemHeight(24);
		self.l.setFont(0, gFont("Regular", 20))
		path_raw = __file__.split("/")
		path = ""
		for x in range(len(path_raw)-1):
			path += (path_raw[x] + "/")
		self.tv_pixmap = LoadPixmap(path + 'tv.png')
		self.hdtv_pixmap = LoadPixmap(path + 'hdtv.png')
		self.radio_pixmap = LoadPixmap(path + 'radio.png')
		self.data_pixmap = LoadPixmap(path + 'data.png')
		self.unkonwn_pixmap = LoadPixmap(path + 'unknown.png')

	def setEntries(self, servicesList):
		east = _("E")
		west = _("W")
		dvbc = _("DVB-C")
		dvbt = _("DVB-T")
		calc_xpos = lambda a:a[len(a)-1][1]+a[len(a)-1][3]	# vom letzten Entry addieren wir x_pos und x_size und erhalten x_pos des neu Entry
		res = []
		for service in servicesList:
			serviceEntry = []
			serviceEntry.append(service['usk'])
			
			servicetype = service['type']
			if servicetype in ("1","4","5","6","11","22","23","24",):			#SD-Video
				service_png = self.tv_pixmap
			elif servicetype in ("17","25","26","27",):							#HDTV
				service_png = self.hdtv_pixmap
			elif servicetype in ("2","10",):									#Radio
				 service_png = self.radio_pixmap
			elif servicetype in ("3","12","13","14","15","16","128","129",):	#Daten
				 service_png = self.data_pixmap
			else:
				 service_png = self.unkonwn_pixmap
			
			serviceEntry.append(MultiContentEntryPixmapAlphaTest(
						pos = (0, 0),
						size = (24, 24),
						png = service_png,))
#						backcolor = backColor,
#						backcolor_sel = backColorSelected)
			
			if int(service.get("flags",0)) & dxDontshow:
#				border_color = 0x00800000
#				border_width = 2
				backcolor = 0x00FF0000
				backcolor_sel = 0x00800080
			else:
#				border_color = 0x000C4E90
#				border_width = 1
				backcolor = None
				backcolor_sel = None
				
			serviceEntry.append(MultiContentEntryText(
#						pos = (0,0),
						pos = (calc_xpos(serviceEntry),0),
						size = (276, 24),
						font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
						text = service['name'],
#						color = 0x00AABBCC,
						backcolor = backcolor,
						backcolor_sel = backcolor_sel,
						border_width = 1,
						border_color = 0x000C4E90))
				
			serviceEntry.append(MultiContentEntryText(
						pos = (calc_xpos(serviceEntry),0),
						size = (155, 24),
						font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP,
						text = service['provider'],
#						color = 0x00AABBCC,
#						backcolor = 0x00AA00CC,
						border_width = 1,
						border_color = 0x000C4E90))
			
			pos = int(service['namespace'],16) >> 16
			if pos == 0xFFFF:
				pos =  dvbc
			elif pos == 0xEEEE:
				pos =  dvbt
			else:
				if pos > 3599:
					pos = _("Error")
				elif pos > 1799:
					pos = 3600 - pos
					pos = "%s.%s %s" %(str(pos/10), str(pos%10), west)
				elif pos > 0:
					pos = "%s.%s %s" %(str(pos/10), str(pos%10), east)
				else:
					pos = "0.0"
			serviceEntry.append(MultiContentEntryText(
						pos = (calc_xpos(serviceEntry),0),
						size = (78, 24),
						font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
						text = pos,
#						color = 0x00AABBCC,
#						backcolor = 0x00AA00CC,
						border_width = 1,
						border_color = 0x000C4E90))
			res.append(serviceEntry)
		self.l.setList(res)
		
class ServiceEditor(Screen,ConfigListScreen):
#	dxNoSDT=1    	# don't get SDT
#	dxDontshow=2
#	dxNoDVB=4		# dont use PMT for this service ( use cached pids )
#	dxHoldName=8
#	dxNewFound=64
	
	skin = """
		<screen position="90,95" size="560,430" title="Edit" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget name="config" position="10,50" size="540,375" scrollbarMode="showOnDemand" />
		</screen>"""
	def __init__(self, session, service = None):
		self.skin = ServiceEditor.skin
		Screen.__init__(self, session)
		self.service = service
		print service
		
		self.serviceVPid = "0000"
		self.serviceVType = "0000"
		self.serviceAPid = "0000"
		self.serviceTPid = "0000"
		self.servicePPid = "0000"
		self.serviceAC3Pid = "0000"
		self.serviceAChannel = "0000"
		self.serviceAC3Delay = "0000"
		self.servicePCMDelay = "0000"
		self.serviceSubtitle = "0000"
		
		if self.service is not None:
			self.serviceName = self.service["name"]
			self.serviceProvider = self.service["provider"]
			self.serviceFlags = self.service.get("flags","0")
			self.serviceSid = self.service["sid"]
			self.serviceType = self.service["type"]
			cacheIDs = self.service.get("cacheIDs",None)
			if cacheIDs is not None:
				for x in cacheIDs:
					pidtype=int(x[:-4],16)
					pid = x[-4:]
					if pidtype == VIDEO_PID:
						self.serviceVPid = pid
					elif pidtype == AUDIO_PID:
						self.serviceAPid = pid
					elif pidtype == TXT_PID:
						self.serviceTPid = pid
					elif pidtype == PCR_PID:
						self.servicePPid = pid
					elif pidtype == AC3_PID:
						self.serviceAC3Pid = pid
					elif pidtype == AUDIOCHANNEL:
						self.serviceAChannel = pid
					elif pidtype == AC3_DELAY:
						self.serviceAC3Delay = pid
					elif pidtype == PCM_DELAY:
						self.servicePCMDelay = pid
					elif pidtype == SUBTITLE_PID:
						self.serviceSubtitle = pid
					elif pidtype == VIDEOTYPE:
						self.serviceVType = pid
		else:
			self.serviceName = "new service"
			self.serviceProvider = "new provider"
			self.serviceFlags = "40"
			self.serviceSid = "0000"
			self.serviceType = "0"
			self.serviceVType = "0000"
		self.flags = int(self.serviceFlags,16)
		self.flag_dxNoSDT = (self.flags & dxNoSDT) and True
		self.flag_dxDontshow = (self.flags & dxDontshow) and True
		self.flag_dxNoDVB = (self.flags & dxNoDVB) and True
		self.flag_dxHoldName = (self.flags & dxHoldName) and True
		self.flag_dxNewFound = (self.flags & dxNewFound) and True

		self.createConfig()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
			{
				"cancel": self.cancel,
				"ok": self.okExit,
				"green": self.okExit,
			},-1)
		self["key_red"] = Button("")
		self["key_green"] = Button(_("ok"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.onLayoutFinish.append(self.layoutFinished)
		self.createSetup()
	
	def layoutFinished(self):
		self.setTitle("Edit " + self.serviceName)

	def createConfig(self):
		self.configServiceName = ConfigText(default = self.serviceName, visible_width = 150, fixed_size = False)
		self.configServiceProvider = ConfigText(default = self.serviceProvider, visible_width = 150, fixed_size = False)
		self.configServiceSid = ConfigHexNumber(default = self.serviceSid)
		self.configServiceVPid = ConfigHexNumber(default = self.serviceVPid)
		self.configServiceVType = ConfigHexNumber(default = self.serviceVType)		#TODO ConfigSelection
		self.configServiceAPid = ConfigHexNumber(default = self.serviceAPid)
		self.configServiceTPid = ConfigHexNumber(default = self.serviceTPid)
		self.configServiceSPid = ConfigHexNumber(default = self.serviceSubtitle)
		self.configServicePPid = ConfigHexNumber(default = self.servicePPid)
		self.configServiceAC3Pid = ConfigHexNumber(default = self.serviceAC3Pid)
		
		self.configServiceAChannel = ConfigInteger(default = int(self.serviceAChannel,16), limits = (0,2))				#TODO �berpr�fen und ConfigSelection daraus machen
		
		self.configServiceAC3Delay = ConfigInteger(default = int(self.serviceAC3Delay,16), limits = (0, 65535))		#TODO Limit �berpr�fen !!!
		self.configServicePCMDelay = ConfigInteger(default = int(self.servicePCMDelay,16), limits = (0, 65535))		#TODO Limit �berpr�fen !!!
		
		self.configSatelliteFlag_dxNoSDT = ConfigYesNo(default = self.flag_dxNoSDT)
		self.configSatelliteFlag_dxDontshow = ConfigYesNo(default = self.flag_dxDontshow)
		self.configSatelliteFlag_dxNoDVB = ConfigYesNo(default = self.flag_dxNoDVB)
		self.configSatelliteFlag_dxHoldName = ConfigYesNo(default = self.flag_dxHoldName)
		self.configSatelliteFlag_dxNewFound = ConfigYesNo(default = self.flag_dxNewFound)
	
	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Name"), self.configServiceName))
		self.list.append(getConfigListEntry(_("Provider"), self.configServiceProvider))
		self.list.append(getConfigListEntry(_("SID (hex)"), self.configServiceSid))
		self.list.append(getConfigListEntry(_("PCR PID (hex)"), self.configServicePPid))
		self.list.append(getConfigListEntry(_("Video PID (hex)"), self.configServiceVPid))
		self.list.append(getConfigListEntry(_("Video Type"), self.configServiceVType))
		self.list.append(getConfigListEntry(_("Audio PID (hex)"), self.configServiceAPid))
		self.list.append(getConfigListEntry(_("AC3 PID (hex)"), self.configServiceAC3Pid))
		self.list.append(getConfigListEntry(_("Audiochannel"), self.configServiceAChannel))
		
		self.list.append(getConfigListEntry(_("AC3 Delay (ms)"), self.configServiceAC3Delay))
		self.list.append(getConfigListEntry(_("PCM Delay (ms)"), self.configServicePCMDelay))
		
		self.list.append(getConfigListEntry(_("TXT PID (hex)"), self.configServiceTPid))
		self.list.append(getConfigListEntry(_("Subtitle PID (hex)"), self.configServiceSPid))
		self.list.append(getConfigListEntry(_("dont use SDT"), self.configSatelliteFlag_dxNoSDT))
		self.list.append(getConfigListEntry(_("hide Service"), self.configSatelliteFlag_dxDontshow))
		self.list.append(getConfigListEntry(_("no standart service"), self.configSatelliteFlag_dxNoDVB))
		self.list.append(getConfigListEntry(_("keep Servicename"), self.configSatelliteFlag_dxHoldName))
		self.list.append(getConfigListEntry(_("sign as new Service"), self.configSatelliteFlag_dxNewFound))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
	
	def cancel(self):
		self.close(None)

	def okExit(self):
		self.serviceVPid = self.configServiceVPid.value
		self.serviceVType = self.configServiceVType.value
		self.serviceAPid = self.configServiceAPid.value
		self.serviceTPid = self.configServiceTPid.value
		self.servicePPid = self.configServicePPid.value
		self.serviceAC3Pid = self.configServiceAC3Pid.value
		self.serviceAChannel = hex(self.configServiceAChannel.value)[2:].zfill(4)
		self.serviceAC3Delay = hex(self.configServiceAC3Delay.value)[2:].zfill(4)
		self.servicePCMDelay = hex(self.configServicePCMDelay.value)[2:].zfill(4)
		self.serviceSubtitle = self.configServiceSPid.value

		if self.serviceVPid == "0000" \
			and self.serviceVType == "0000" \
			and self.serviceAPid == "0000" \
			and self.serviceTPid == "0000" \
			and self.servicePPid == "0000" \
			and self.serviceAC3Pid == "0000" \
			and self.serviceAChannel == "0000" \
			and self.serviceAC3Delay == "0000" \
			and self.servicePCMDelay == "0000" \
			and self.serviceSubtitle == "0000" \
			and "cacheIDs" in self.service:
				del self.service["cacheIDs"]
		else:
			self.service["cacheIDs"] = []
			if self.serviceVPid != "0000":
				self.service["cacheIDs"].append(str(hex(VIDEO_PID)[2:].zfill(2) + self.serviceVPid))
			if self.serviceAPid != "0000":
				self.service["cacheIDs"].append(str(hex(AUDIO_PID)[2:].zfill(2) + self.serviceAPid))
			if self.serviceTPid != "0000":
				self.service["cacheIDs"].append(str(hex(TXT_PID)[2:].zfill(2) + self.serviceTPid))
			if self.servicePPid != "0000":
				self.service["cacheIDs"].append(str(hex(PCR_PID)[2:].zfill(2) + self.servicePPid))
			if self.serviceAC3Pid != "0000":
				self.service["cacheIDs"].append(str(hex(AC3_PID)[2:].zfill(2) + self.serviceAC3Pid))
			if self.serviceVType != "0000":
				self.service["cacheIDs"].append(str(hex(VIDEOTYPE)[2:].zfill(2) + self.serviceVType))
			if self.serviceAChannel != "0000":
				self.service["cacheIDs"].append(str(hex(AUDIOCHANNEL)[2:].zfill(2) + self.serviceAChannel))
			if self.serviceAC3Delay != "0000":
				self.service["cacheIDs"].append(str(hex(AC3_DELAY)[2:].zfill(2) + self.serviceAC3Delay))
			if self.servicePCMDelay != "0000":
				self.service["cacheIDs"].append(str(hex(PCM_DELAY)[2:].zfill(2) + self.servicePCMDelay))
			if self.serviceSubtitle != "0000":
				self.service["cacheIDs"].append(str(hex(SUBTITLE_PID)[2:].zfill(2) + self.serviceSubtitle))

		self.service.update({"sid":str(self.configServiceSid.value)})
		
		self.service.update({"name":self.configServiceName.value})
		
		self.service.update({"Provider":self.configServiceProvider.value})
		
		flags =  (self.configSatelliteFlag_dxNoSDT.value * dxNoSDT) \
			+(self.configSatelliteFlag_dxDontshow.value * dxDontshow) \
			+(self.configSatelliteFlag_dxNoDVB.value * dxNoDVB) \
			+(self.configSatelliteFlag_dxHoldName.value * dxHoldName) \
			+(self.configSatelliteFlag_dxNewFound.value * dxNewFound)
		self.service.update({"flags":hex(flags)[2:].zfill(4)})
		
		print self.service
		self.close(self.service)

class Laufschrift(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
		self.l.setItemHeight(24);
		self.l.setFont(0, gFont("Regular", 20))
		path_raw = __file__.split("/")
		path = ""
		for x in range(len(path_raw)-1):
			path += (path_raw[x] + "/")
		self.type_pixmap = LoadPixmap(path + 'type.png')
		self.myTimer = eTimer()
		self.myTimer.callback.append(self.laufschrift)
		self.myTimer.start(60)
		self.offset = 24
		self.mylist = None
	
	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def laufschrift(self):
		if self.mylist is None:
			return
		self.offset=-((abs(self.offset)+1)%43)
		self.mylist[1][1]=self.offset
		tmp = []
		for x in self.mylist:
			if x is not None and len(x)>1:
				tmp.append(tuple(x))
			else:
				tmp.append(x)
		self.l.setList([tmp])
	
	def setEntry(self):
		res = [None]
		res.append(MultiContentEntryPixmapAlphaTest(
			pos = (0, 0),
			size = (67,24),
			png = self.type_pixmap,))
		tmp = []
		for x in res:
			if x is not None and len(x)>1:
				tmp2 = []
				for y in x:
					tmp2.append(y)
				tmp.append(tmp2)
			else:
				tmp.append(x)
		self.mylist = tmp
		self.l.setList([res])


class Head(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0,0,0,0))
		self.l.setItemHeight(24);
		self.l.setFont(0, gFont("Regular", 20))
	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def setEntries(self,data = None):
		if data is None:
			return
		res = [None]
		for x in data:
			res.append(MultiContentEntryText(
				pos = (x[0],0),
				size = (x[1], 24),
				font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
				text = x[2],
				color = 0x00C0C0C0,
				backcolor = 0x25474738,
				color_sel = 0x00FFFFFF,
				backcolor_sel = 0x00204060,
				border_width = 1,
				border_color = 0x000C4E90))
		self.l.setList([res])

class ServiceHideMenuSelection(Screen):
	skin = """
		<screen position="90,165" size="500,130" title="">
			<widget name="menulist" position="20,10" size="460,100" />
		</screen>"""
		
	def __init__(self, session, service = None):
		Screen.__init__(self, session)

		if service is None:
			self.close(None)

		actionList = []
		if int(service.get("flags",0)) & dxDontshow:
			actionList.append(_("unhide Service %s" %service["name"]))
		else:
			actionList.append(_("hide Service %s" %service["name"]))
		actionList.append(_("hide Provider %s") %service["provider"])
		actionList.append(_("unhide Provider %s") %service["provider"])
		actionList.append(_("toggle hide attibutes for %s") %service["provider"])

		self["menulist"] = MenuList(actionList)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick,
			"cancel": self.cancel,
		}, -1)
		self.onLayoutFinish.append(self.layoutFinished)
		
	def layoutFinished(self):
		self.setTitle(_("Options for hide"))

	def okbuttonClick(self):
		print "okbuttonClick"
		self.close(self["menulist"].getSelectionIndex())
	
	def cancel(self):
		self.close(None)

class ServicesEditor(Screen):

	version = "(20090416-alpha)"
	skin = """
		<screen position="90,95" size="560,430" title="reading lamedb - please wait" >
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget name="laufschrift" position="0,40" size="24,24" scrollbarMode="showNever" />
		<widget name="head" position="24,40" size="536,24" scrollbarMode="showNever" />
		<widget name="list" position="0,64" size="560,240" scrollbarMode="showOnDemand" />
		<widget name="infolist" position="0,334" size="560,96" />
		</screen>"""
	def __init__(self, session):
		self.skin = ServicesEditor.skin
		Screen.__init__(self, session)

		self.servicesList = []
		self.usk = None
		self.cur_service = None
		self.mainTitle = "ServicesEditor %s" %self.version
		self["actions"] = ActionMap(["ServicesEditorActions"],
			{
				"nextPage"			: self.nextPage,
				"nextPageUp"		: self.selectionKeyUp,
				"nextPageRepeated"	: self.nextPageRepeated,
				"prevPage"			: self.prevPage,
				"prevPageUp"		: self.selectionKeyUp,
				"prevPageRepeated"	: self.prevPageRepeated,
				"displayHelp"		: self.showHelp,
				"displayMenu"		: self.openMenu,
				"displayInfo"		: self.showServiceInfo,
				"select"			: self.editService,
				"exit"				: self.Exit,
				"left"				: self.left,
				"leftUp"			: self.doNothing,
				"leftRepeated"		: self.doNothing,
				"right"				: self.right,
				"rightUp"			: self.doNothing,
				"rightRepeated"		: self.doNothing,
				"upUp"				: self.selectionKeyUp,
				"up"				: self.up,
				"upRepeated"		: self.upRepeated,
				"down" 				: self.down,
				"downUp"			: self.selectionKeyUp,
				"downRepeated"		: self.downRepeated,
				"redUp"				: self.hideService,
				"redLong"			: self.hideServiceMenu,
				"green"				: self.editService,
				"yellow"			: self.addService,
				"blue"				: self.sortColumn,
			},-1)

		self["key_red"] = Button(_("hide/unhide"))
		self["key_green"] = Button(_("edit"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("sort"))

		self["infolist"] = MenuList([])
		self["infolist"].l = eListboxPythonMultiContent()
		self["infolist"].l.setSelectionClip(eRect(0,0,0,0))
		self["infolist"].l.setItemHeight(24);
		self["infolist"].l.setFont(0, gFont("Regular", 20))
		
		self["laufschrift"] = Laufschrift()
		self["head"] = Head()
		self["list"] = ServiceList()
		self.onLayoutFinish.append(self.layoutFinished)
		self.currentSelectedColumn = 1
		
#row [["kennung","sichtbarer Text", Sortierrichtung]],
		self.row = [
			["name", _("Services"), False],
			["provider", _("Providers"), False],
			["position", _("Pos"), False],
			]
		self.typesort = False
		
		self.myTimer = eTimer()
		db = eDVBDB.getInstance()
		db.saveServicelist()
		self.lamedb = Lamedb()
		self.database = self.lamedb.database
		self._initFlag = False

	def layoutFinished(self):
		self.myTimer.callback.append(self.initDatabase)
		self.myTimer.start(1000)

	def initDatabase(self):
		self.myTimer.start(200)
		if self.lamedb.databaseState < 3:
			self.setTitle("reading lamedb - please wait - get transponders")
			return
		elif self.lamedb.databaseState == 3:
			self.setTitle("reading lamedb - please wait - get services %s"%str(self.lamedb.readcnt))
			return
		elif self.lamedb.databaseState == 4:
			self.setTitle("reading lamedb - please wait - build database")
			self.lamedb.databaseState = 5
			return
		self.myTimer.stop()
		self.buildServicesList()
		row = self["list"].getCurrent()
		if row is None:
			return
		head = []
		for x in xrange(2,len(row)):	#bei zwei anfangen, weil eins die Laufschrift ist
			head.append([row[x][1]-row[1][3],row[x][3],""])
		for x in xrange(len(self.row)):
			head[x][2]= self.row[x][1]
			if len(self.row[x])>3:		#TODO Graphik
				head[x].append(True)		#Platzhalter f�r Graphik
				
		self["laufschrift"].setEntry()
		self["head"].setEntries(head)
		if self.currentSelectedColumn:
			data = self["head"].l.getCurrentSelection()
			data = data[self.currentSelectedColumn]
			self["head"].l.setSelectionClip(eRect(data[1], data[0], data[3], data[4]), True)
		else:
			self["head"].l.setSelectionClip(eRect(0, 0, 0, 0))
#			self["laufschrift"]..l.setSelectionClip(eRect(data[1], data[0], data[3], data[4]), True)
		
		self.updateSelection()
		self.setTitle(self.mainTitle)
		
	def buildServicesList(self):
		self.servicesList = []
		for tp in self.database:
			for uniqusServiceKey in self.database[tp]["services"]:
				self.servicesList.append(self.database[tp]["services"][uniqusServiceKey])
		self["list"].setEntries(self.servicesList)

	def updateSelection(self):
		row = self["list"].l.getCurrentSelection()
		if row is None:
			self.usk = None
			self.cur_service = None
			return
		self.usk = self["list"].l.getCurrentSelection()[0]
		self.cur_service = self.database[self.usk[:16]]["services"][self.usk]
		firstColumn = row[1]	#wir fangen bei der zweiten Spaltean, das ServicetypeIcon wird also nicht mit selectiert
		lastColumn = row[len(row)-1]
#sollte doch das Icon mit selectiert werden, dann ist darauf zu achten, das das Icon KEINEN Rand hat und lastColumn[0] anstat firstColumb[0] verwendet werden muss
# um eine korrekte Anzeige des Selectionsbalken zu erhalten
		self["list"].l.setSelectionClip(eRect(firstColumn[1], lastColumn[0], lastColumn[1]+lastColumn[3], lastColumn[4]), True) #
		self.getInfo()

	def doNothing(self):
		pass
		
	def left(self):
		print "left"
		if self.currentSelectedColumn:
			data = self["head"].l.getCurrentSelection()
			if data is  None:
				return
			self.currentSelectedColumn -= 1
			if self.currentSelectedColumn:
				data_c = data[self.currentSelectedColumn]
				data_c2 = data[self.currentSelectedColumn +1]
				x1 = data_c2[1]
				x0 = data_c[1]
				if x0 < 0:
					x0 = 0
				self["head"].l.setSelectionClip(eRect(x0, data_c[0], x1-x0, data_c[4]), True)
			else:
				self["head"].l.setSelectionClip(eRect(0,0,0,0), True)
#				self["laufschrift"]..l.setSelectionClip(eRect(data[1], data[0], data[3], data[4]), True)
		elif self["head"].l.getCurrentSelection() is not None:
			self["head"].l.setSelectionClip(eRect(0,0,0,0))

	def right(self):
		print "right"
		if self.currentSelectedColumn < len(self.row):
			data = self["head"].l.getCurrentSelection()
			if data is  None:
				return
			self.currentSelectedColumn += 1
			data = data[self.currentSelectedColumn]
			self["head"].l.setSelectionClip(eRect(data[1], data[0], data[3], data[4]), True)	
	
	def nextPage(self):
		self["list"].pageUp()
		self.lastSelectedIndex = self["list"].getSelectedIndex()
		self.updateSelection()

	def prevPage(self):
		self["list"].pageDown()
		self.lastSelectedIndex = self["list"].getSelectedIndex()
		self.updateSelection()
	
	def nextPageRepeated(self):
		self["list"].pageUp()
#		self.updateSelection()

	def prevPageRepeated(self):
		self["list"].pageDown()
#		self.updateSelection()
		
	def selectionKeyUp(self):
		cur_idx = self["list"].getSelectedIndex()
		if self.lastSelectedIndex != cur_idx:
			self.updateSelection()
			self.lastSelectedIndex = cur_idx
	
	def up(self):
		self["list"].up()
		self.lastSelectedIndex = self["list"].getSelectedIndex()
		self.updateSelection()

	def down(self):
		self["list"].down()
		self.lastSelectedIndex = self["list"].getSelectedIndex()
		self.updateSelection()
	
	def upRepeated(self):
		self["list"].up()
		self.updateSelection()
	
	def downRepeated(self):
		self["list"].down()
		self.updateSelection()

	def getInfo(self):
		transPol = {
			"0":"H",
			"1":"V",
			"2":"L",
			"3":"R",
			}
		transFec = {
			"0":"auto",
			"1":"1/2",
			"2":"2/3",
			"3":"3/4",
			"4":"5/6",
			"5":"7/8",
			"6":"8/9",
			"7":"3/5",
			"8":"4/5",
			"9":"9/10",
			}
		transFecTerr = {
			"0":"1/2",
			"1":"2/3",
			"2":"3/4",
			"3":"5/6",
			"4":"7/8",
			"5":"auto",
			}
		transModulation = {
			"1":"QPSK",
			"2":"8PSK",
			"3":"QAM16",
			}
			
		transModulationCable = {
			"0":"auto",
			"1":"QAM16",
			"2":"QAM32",
			"3":"QAM64",
			"4":"QAM128",
			"5":"QAM256",
			}
			
		transModulationTerr = {
			"0":"QPSK",
			"1":"QAM16",
			"2":"QAM64",
			"3":"auto",
			}
			
		transBandwidth = {
			"0":"8MHz",
			"1":"7MHz",
			"2":"6MHz",
			"3":"auto",
			}

		print "getInfo"
		self["infolist"].l.setFont(0, gFont("Regular", 20))
		utk = self.usk[:16]
		name = self.cur_service["name"]
		provider = self.cur_service["provider"]
		flags = self.cur_service.get("flags","0")
		tp = self.database.get(utk,None)
		if tp is not None:
			freq = tp["frequency"]
			if self.usk[:4].lower()=="ffff":
				sym = tp["symbol_rate"]
				fec = tp.get("fec_inner","0")
				mod = tp.get("modulation","0")
				info3 = (
					(100, freq[:-3]+"."+freq[-3:]),
					(60, sym[:-3]),
					(50, transFec.get(fec,"?")),
					(80, transModulationCable.get(mod,"?")),
					(55, self.cur_service.get("type","?")),
				)
			elif self.usk[:4].lower()=="eeee":
				bw = tp["bandwidth"]
				fecHP = tp["code_rate_HP"]
				fecLP = tp["code_rate_LP"]
				mod = tp["modulation"]
				info3 = (
					(100, freq[:-6]+"."+freq[-6:-3]),
					(50, transBandwidth.get(bw,"?")),
					(50, transFecTerr.get(fecHP,"?")),
					(50, transFecTerr.get(fecLP,"?")),
					(80, transModulationTerr.get(mod,"?")),
				)
			else:
				sys = tp.get("system",None)
				if sys is None:
					sys = "0"
					mod = "1"
				else:
					mod = tp.get("modulation","1")
	#				rolloff
				pol = tp["polarization"]
				sym = tp["symbol_rate"]
				fec = tp.get("fec_inner","0")
				print sys, freq, pol, sym, fec, mod
				info3 = (		
					(100, freq[:-3]+"."+freq[-3:]),
					(15, transPol.get(pol,"?")),
					(60, sym[:-3]),
					(50, transFec.get(fec,"?")),
					(55, transModulation.get(mod,"?")),
					(55, self.cur_service.get("type","?")),
					)

		calc_xpos = lambda a:a[len(a)-1][1]+a[len(a)-1][3]	# vom letzten Entry addieren wir x_pos und x_size und erhalten x_pos des neu Entry
		l = []
#erste Zeile: Servicename
		entry = [None]
		entry.append(MultiContentEntryText(
			pos = (0,0),
			size = (560, 24),
			font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
			text = name,
			border_width = 1,
			border_color = 0x000C8E90))
		l.append(entry)
#zweite Zeile Provider
		entry = [None]
		entry.append(MultiContentEntryText(
			pos = (0,0),
			size = (560, 24),
			font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
			text = provider,
			border_width = 1,
			border_color = 0x000C8E90))
		l.append(entry)
#dritte Zeile
		entry = [None]
		for i in info3:
			if len(entry)==1:
				entry.append(MultiContentEntryText(
					pos = (0,0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
			else:
				entry.append(MultiContentEntryText(
					pos = (calc_xpos(entry),0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
		l.append(entry)
#vierte Zeile
		cacheIDs =self.cur_service.get("cacheIDs",None)
		vpid = "----"
		apid = "----"
		tpid = "----"
		pcrpid = "----"
		ac3pid = "----"
		achannel = "----"
		ac3delay = "----"
		pcmdelay = "----"
		spid = "----"
		vtype = "----"
	
		if cacheIDs is not None:
			for x in cacheIDs:
				pidtype=int(x[:-4],16)
				pid = x[-4:]
				print "type:",pidtype
				print "pid:",pid
				if pidtype == VIDEO_PID:
					vpid = pid
				elif pidtype == AUDIO_PID:
					apid = pid
				elif pidtype == TXT_PID:
					tpid = pid
				elif pidtype == PCR_PID:
					pcrpid = pid
				elif pidtype == AC3_PID:
					ac3pid = pid
				elif pidtype == AUDIOCHANNEL:
					achannel = pid
				elif pidtype == AC3_DELAY:
					ac3delay = pid
				elif pidtype == PCM_DELAY:
					pcmdelay = pid
				elif pidtype == SUBTITLE_PID:
					spid = pid
				elif pidtype == VIDEOTYPE:
					vtype = pid
					
		info4 = (
			(50, vpid),
			(50, vtype),
			(50, apid),
			(50, tpid),
			(50, spid),
			(50, pcrpid),
			(50, ac3pid),
			(50, achannel),
			(50, ac3delay),
			(50, pcmdelay),
			)
		
		entry = [None]
		for i in info4:
			if len(entry)==1:
				entry.append(MultiContentEntryText(
					pos = (0,0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
			else:
				entry.append(MultiContentEntryText(
					pos = (calc_xpos(entry),0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
		l.append(entry)
		
		self["infolist"].l.setList(l)


	def addService(self):
		print "addService"
	
	def editService(self):
		print "editService"
		if self.cur_service is None:
			return
		self.session.openWithCallback(self.finishedServiceEdit, ServiceEditor, self.cur_service)

	def hideService(self):
		print "hideService"
		self.cur_service["flags"]=str(int(self.cur_service.get("flags","0")) ^ dxDontshow)
		self["list"].setEntries(self.servicesList)
	
	def hideServiceMenu(self):
		print "hideServiceMenu"
		self.session.openWithCallback(self.serviceHideMenu, ServiceHideMenuSelection, self.cur_service)
	
	def serviceHideMenu(self, result):
		if result == 0:
			self.cur_service["flags"]=str(int(self.cur_service.get("flags","0")) ^ dxDontshow)
		elif result == 1:
			print "hide all"
			for tp in self.database:
				for usk in self.database[tp]["services"]:
					service = self.database[tp]["services"][usk]
					print service["provider"]
					if service["provider"] == self.cur_service["provider"]:
						service["flags"]=str(int(service.get("flags","0")) | dxDontshow)
		elif result == 2:
			print "unhide all"
			for tp in self.database:
				for usk in self.database[tp]["services"]:
					service = self.database[tp]["services"][usk]
					if service["provider"] == self.cur_service["provider"]:
						service["flags"]=str(int(service.get("flags","0")) & ~dxDontshow)
		elif result == 3:
			print "toggle"
			for tp in self.database:
				for usk in self.database[tp]["services"]:
					service = self.database[tp]["services"][usk]
					if service["provider"] == self.cur_service["provider"]:
						service["flags"]=str(int(service.get("flags","0")) ^ dxDontshow)
		else:
			print "Men�fehler:",result
			return
		self["list"].setEntries(self.servicesList)
	
	def finishedServiceEdit(self, result):
		if result is None:
			return
		for idx in xrange(len(self.servicesList)):
			if self.servicesList[idx]["usk"] == result["usk"]:
				self["list"].instance.moveSelectionTo(idx)
				self.servicesList[idx] = result
				self["list"].setEntries(self.servicesList)
				break
		self.updateSelection()

	def compareColumn(self, a):
#das lower() dient dazu, dass Gro�/Kleinschreibung nicht benutzt wird
		if self.currentSelectedColumn:
			if self.row[self.currentSelectedColumn-1][0] == "name":
				return a.get("name").lower()
			elif self.row[self.currentSelectedColumn-1][0] == "provider":
				return a.get("provider").lower()
			elif self.row[self.currentSelectedColumn-1][0] == "position":
				return int(a.get('namespace',"0"),16) >> 16
		else:
			return int(a.get('type',"0"),10)
	
	def sortColumn(self):
		if self.cur_service is None:
			return
		if self.currentSelectedColumn:
			rev = self.row[self.currentSelectedColumn-1][2]
			self.servicesList.sort(key = self.compareColumn, reverse = rev)
			if rev:
				self.row[self.currentSelectedColumn-1][2] = False
			else:
				self.row[self.currentSelectedColumn-1][2] = True
		else:
			rev = self.typesort
			self.servicesList.sort(key = self.compareColumn, reverse = rev)
			if rev:
				self.typesort = False
			else:
				self.typesort = True
			
		self["list"].setEntries(self.servicesList)
		for idx in xrange(len(self.servicesList)):
			if self.servicesList[idx]["usk"] == self.usk:
				self["list"].instance.moveSelectionTo(idx)
				break
		self.updateSelection()

	def openMenu(self):
		print "openMenu"

	def Exit(self):
		if self.lamedb.databaseState == 5:
			self.lamedb.writeLamedb()
			db = eDVBDB.getInstance()
			db.removeServices(int("-0x10000",16), -1, -1, 0xFFFFFFFF)
			db.removeServices(int("-0x11120000",16), -1, -1, 0xFFFFFFFF)
			for x in self.database:
				db.removeServices(-1, -1, -1, int(x[:4],16))
			db.reloadServicelist()
		self.close()
		
	def showServiceInfo(self):
		print "showServiceInfo"
	
	def showHelp(self):
		print "showHelp"
		if self.cur_service is None:
			return
		self["infolist"].l.setFont(0, gFont("Regular", 11))
		calc_xpos = lambda a:a[len(a)-1][1]+a[len(a)-1][3]	# vom letzten Entry addieren wir x_pos und x_size und erhalten x_pos des neu Entry
		l = []
#erste Zeile: Servicename
		entry = [None]
		entry.append(MultiContentEntryText(
			pos = (0,0),
			size = (560, 24),
			font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
			text = _("Service"),
			border_width = 1,
			border_color = 0x000C8E90))
		l.append(entry)
#zweite Zeile Provider
		entry = [None]
		entry.append(MultiContentEntryText(
			pos = (0,0),
			size = (560, 24),
			font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
			text = _("Provider"),
			border_width = 1,
			border_color = 0x000C8E90))
		l.append(entry)
#dritte Zeile
		entry = [None]
		if self.usk[:4].lower()=="ffff":
			info3 = (
				(100, _("Frequency\nMHz")),
				(60, "Symbolrate\nkSym"),
				(50, "FEC"),
				(80, "Modulation"),
				(55, "Service\nType"),
			)
		elif self.usk[:4].lower()=="eeee":
			info3 = (
				(100, _("Frequency\nMHz")),
				(50, "Bandwidth"),
				(50, "Code rate\nHP"),
				(50, "Code rate\nLP"),
				(80, "Modulation"),
				(55, "Service\nType"),
				)
		else:
			info3 = (
				(100, _("Frequency\nMHz")),
				(15, "P"),
				(60, "Symbolrate\nkSym"),
				(50, "FEC"),
				(55, "Modulation"),
				(55, "Service\nType"),
				)
		for i in info3:
			if len(entry)==1:
				entry.append(MultiContentEntryText(
					pos = (0,0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
			else:
				entry.append(MultiContentEntryText(
					pos = (calc_xpos(entry),0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
		l.append(entry)
#vierte Zeile
		vpid = "Video\nPID (hex)"
		vtype = "Video\nType"
		apid = "Audio\nPID (hex)"
		tpid = "TXT\nPID (hex)"
		spid = "Subtitle\nPID (hex)"
		pcrpid = "PCR\nPID (hex)"
		ac3pid = "AC3\nPID (hex)"
		achannel = "Audio\nCannel"
		ac3delay = "AC3\nDelay"
		pcmdelay = "PCM\nDelay"
	
		info4 = (
			(50, vpid),
			(50, vtype),
			(50, apid),
			(50, tpid),
			(50, spid),
			(50, pcrpid),
			(50, ac3pid),
			(50, achannel),
			(50, ac3delay),
			(50, pcmdelay),
			)
		entry = [None]
		for i in info4:
			if len(entry)==1:
				entry.append(MultiContentEntryText(
					pos = (0,0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
			else:
				entry.append(MultiContentEntryText(
					pos = (calc_xpos(entry),0),
					size = (i[0], 24),
					font = 0, flags = RT_HALIGN_CENTER | RT_VALIGN_TOP,
					text = i[1],
					border_width = 1,
					border_color = 0x000C8E90))
		l.append(entry)
		
		self["infolist"].l.setList(l)

def ServicesEditorMain(session, **kwargs):
	session.open(ServicesEditor)

def ServicesEditorStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Services Editor"), ServicesEditorMain, "Services Editor", None)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Services Editor"), description="Lets you edit services in your Dreambox", where = PluginDescriptor.WHERE_MENU, fnc=ServicesEditorStart)
