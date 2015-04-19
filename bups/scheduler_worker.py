#!/usr/bin/env python2

import sys
import config
from manager import BupManager

manager = BupManager(config.read(sys.argv[1]))

def onstatus(status, ctx):
	print(status)

def onerror(err, ctx):
	sys.stderr.write(err+"\n")

callbacks = {
	"onstatus": onstatus,
	"onerror": onerror
}

manager.backup(callbacks)