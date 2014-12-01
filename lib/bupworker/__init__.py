#!/usr/bin/env python2

import sys
sys.path.append('/usr/lib/bup')

import os
from subprocess import PIPE, Popen, call
from gi.repository import GObject
from bup import git
from index import call_index
from save import call_save

class BupWorker:
	def __init__(self, bup_dir=None):
		self.dir = None

		if bup_dir is not None:
			self.set_dir(bup_dir)
		os.environ['BUP_MAIN_EXE'] = 'bup'

	def set_dir(self, bup_dir):
		self.dir = bup_dir
		os.environ['BUP_DIR'] = bup_dir

	def init(self):
		return git.init_repo()

	def index(self, dirpath, opts={}, callbacks={}):
		#return self.run(['index', '-u', dirpath], onread, onread, onclose)
		call_index(dirpath, opts, callbacks)

	def save(self, dirpath, opts={}, callbacks={}):
		#return self.run(['save', '-n', name, dirpath], onread, onread, onclose)
		call_save(dirpath, opts, callbacks)

	def fuse(self, mountPath, callbacks={}):
		self.run(["fuse", mountPath], )

	def run(self, args, callbacks={}):
		env = {}
		if self.dir is not None:
			env = {"BUP_DIR": self.dir}

		# start subprocess
		args.insert(0, "bup")
		proc = Popen(args, env=env, stdout=PIPE, stderr=PIPE)

		# read from subprocess
		def read_data(source, condition, onread):
			line = source.readline() # might block if no newline!
			#line = source.read(1)
			if not line:
				source.close()
				return False # stop reading
			onread(line)
			return True # continue reading
		def read_stdout(source, condition):
			return read_data(source, condition, callbacks["stdout"])
		def read_stderr(source, condition):
			return read_data(source, condition, callbacks["stderr"])

		def closed(source, condition):
			onclose(proc.poll())

		if "stdout" in callbacks:
			GObject.io_add_watch(proc.stdout, GObject.IO_IN, read_stdout)
		if "stderr" in callbacks:
			GObject.io_add_watch(proc.stderr, GObject.IO_IN, read_stderr)
		if "onclose" in callbacks:
			GObject.io_add_watch(proc.stdout, GObject.IO_HUP, callbacks["onclose"])
