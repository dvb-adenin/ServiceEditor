from Components.Language import language
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_LANGUAGE
from os import environ as os_environ
import gettext

def localeInit():
	lang = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
	os_environ["LANGUAGE"] = lang # Enigma doesn't set this (or LC_ALL, LC_MESSAGES, LANG). gettext needs it!
	gettext.bindtextdomain("ServiceEditor", resolveFilename(SCOPE_PLUGINS, "SystemPlugins/ServiceEditor/po/"))

def _(txt):
	t = gettext.dgettext("ServiceEditor", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

def print_rd(txt):
	print "\x1b[31m", txt, "\x1b[0m"

def print_gr(txt):
	print "\x1b[32m", txt, "\x1b[0m"

def print_ye(txt):
	print "\x1b[33m", txt, "\x1b[0m"

def print_bl(txt):
	print "\x1b[34m", txt, "\x1b[0m"

def print_mg(txt):
	print "\x1b[35m", txt, "\x1b[0m"

def print_cy(txt):
	print "\x1b[36m", txt, "\x1b[0m"

localeInit()
language.addCallback(localeInit)

