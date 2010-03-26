# elog/messages.py - elog core functions
# Copyright 2006-2009 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import portage
portage.proxy.lazyimport.lazyimport(globals(),
	'portage.output:colorize',
	'portage.util:writemsg',
)

from portage.const import EBUILD_PHASES
from portage.localization import _
from portage import os
from portage import _encodings
from portage import _unicode_encode
from portage import _unicode_decode

import codecs
import sys

def collect_ebuild_messages(path):
	""" Collect elog messages generated by the bash logging function stored 
		at 'path'.
	"""
	mylogfiles = None
	try:
		mylogfiles = os.listdir(path)
	except OSError:
		pass
	# shortcut for packages without any messages
	if not mylogfiles:
		return {}
	# exploit listdir() file order so we process log entries in chronological order
	mylogfiles.reverse()
	logentries = {}
	for msgfunction in mylogfiles:
		filename = os.path.join(path, msgfunction)
		if msgfunction not in EBUILD_PHASES:
			writemsg(_("!!! can't process invalid log file: %s\n") % filename,
				noiselevel=-1)
			continue
		if not msgfunction in logentries:
			logentries[msgfunction] = []
		lastmsgtype = None
		msgcontent = []
		for l in codecs.open(_unicode_encode(filename,
			encoding=_encodings['fs'], errors='strict'),
			mode='r', encoding=_encodings['repo.content'], errors='replace'):
			if not l:
				continue
			try:
				msgtype, msg = l.split(" ", 1)
			except ValueError:
				writemsg(_("!!! malformed entry in "
					"log file: '%s'\n") % filename, noiselevel=-1)
				continue

			if lastmsgtype is None:
				lastmsgtype = msgtype
			
			if msgtype == lastmsgtype:
				msgcontent.append(msg)
			else:
				if msgcontent:
					logentries[msgfunction].append((lastmsgtype, msgcontent))
				msgcontent = [msg]
			lastmsgtype = msgtype
		if msgcontent:
			logentries[msgfunction].append((lastmsgtype, msgcontent))

	# clean logfiles to avoid repetitions
	for f in mylogfiles:
		try:
			os.unlink(os.path.join(path, f))
		except OSError:
			pass
	return logentries

_msgbuffer = {}
def _elog_base(level, msg, phase="other", key=None, color=None, out=None):
	""" Backend for the other messaging functions, should not be called 
	    directly.
	"""

	global _msgbuffer

	if out is None:
		out = sys.stdout

	if color is None:
		color = "GOOD"

	msg = _unicode_decode(msg,
		encoding=_encodings['content'], errors='replace')

	formatted_msg = colorize(color, " * ") + msg + "\n"

	# avoid potential UnicodeEncodeError
	if out in (sys.stdout, sys.stderr):
		formatted_msg = _unicode_encode(formatted_msg,
			encoding=_encodings['stdio'], errors='backslashreplace')
		if sys.hexversion >= 0x3000000:
			out = out.buffer

	out.write(formatted_msg)

	if key not in _msgbuffer:
		_msgbuffer[key] = {}
	if phase not in _msgbuffer[key]:
		_msgbuffer[key][phase] = []
	_msgbuffer[key][phase].append((level, msg))

	#raise NotImplementedError()

def collect_messages():
	global _msgbuffer

	rValue = _msgbuffer
	_reset_buffer()
	return rValue

def _reset_buffer():
	""" Reset the internal message buffer when it has been processed, 
	    should not be called directly.
	"""
	global _msgbuffer
	
	_msgbuffer = {}

# creating and exporting the actual messaging functions
_functions = { "einfo": ("INFO", "GOOD"),
		"elog": ("LOG", "GOOD"),
		"ewarn": ("WARN", "WARN"),
		"eqawarn": ("QA", "WARN"),
		"eerror": ("ERROR", "BAD"),
}

def _make_msgfunction(level, color):
	def _elog(msg, phase="other", key=None, out=None):
		""" Display and log a message assigned to the given key/cpv 
		    (or unassigned if no key is given).
		""" 
		_elog_base(level, msg,  phase=phase, key=key, color=color, out=out)
	return _elog

import sys
for f in _functions:
	setattr(sys.modules[__name__], f, _make_msgfunction(_functions[f][0], _functions[f][1]))
del f, _functions
