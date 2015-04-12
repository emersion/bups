import os, sys

sys.path.append('/usr/lib/bup')
os.environ['BUP_MAIN_EXE'] = os.path.abspath('/usr/bin/bup')
os.environ['BUP_FORCE_TTY'] = '2'

import time
import json

def progress_format(f, data):
	o = ""
	if f == 'json':
		o = json.dumps(data)

	if o:
		sys.stderr.write(o + '\n')

_last_prog = 0
def qprogress_format(f, data):
	global _last_prog
	now = time.time()
	if now - _last_prog <= 0.1:
		return

	_last_prog = now
	progress_format(f, data)