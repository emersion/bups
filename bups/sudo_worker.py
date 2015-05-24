#!/usr/bin/env python2

import sys
import config
import json
from manager import BupManager

manager = BupManager(config.read(sys.argv[1]))

while True:
	try:
		cmd = raw_input()
	except EOFError, e:
		cmd = 'quit'

	res = {
		"success": True,
		"output": ""
	}

	def onerror(err, ctx):
		res["output"] += err+"\n"

	callbacks = {
		"onerror": onerror
	}

	if cmd == 'quit':
		sys.exit()
	if cmd == 'mount':
		res["success"] = manager.mount_parents(callbacks)
		res["bup_path"] = manager.bup.get_dir()
	if cmd == 'unmount':
		res["success"] = manager.unmount_parents(callbacks)

	sys.stdout.write(json.dumps(res)+"\n")
	sys.stdout.flush()