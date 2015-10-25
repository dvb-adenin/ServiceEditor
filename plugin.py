# -*- coding: UTF-8 -*-
from Lamedb import Lamedb
from ServiceEditor import ServiceEditor
from Plugins.Plugin import PluginDescriptor
from Components.NimManager import nimmanager
from . import *


def ServiceEditorMain(session, **kwargs):
	reload(Lamedb)
	reload(ServiceEditor)
	session.open(ServiceEditor.ServiceListEditor)

def ServiceEditorStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Service Editor"), ServiceEditorMain, "Service Editor", None)]
	else:
		return []

def Plugins(**kwargs):
	return PluginDescriptor(name=_("Service Editor"), description=_("Lets you edit services in your enigma2"), where = PluginDescriptor.WHERE_MENU, fnc=ServiceEditorStart)
