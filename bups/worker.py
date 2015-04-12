#!/usr/bin/env python2

import sys
sys.path.append('/usr/lib/bup')

import os
from subprocess import PIPE, Popen, call
import contextlib
import json
from bup import git
 
# Unix, Windows and old Macintosh end-of-line
newlines = ['\n', '\r\n', '\r']
def unbuffered(proc, stream='stdout'):
	stream = getattr(proc, stream)
	with contextlib.closing(stream):
		while True:
			out = []
			last = stream.read(1)
			# Don't loop forever
			if last == '' and proc.poll() is not None:
				break
			while last not in newlines:
				# Don't loop forever
				if last == '' and proc.poll() is not None:
					break
				out.append(last)
				last = stream.read(1)
			out = ''.join(out)
			yield out

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
		args = ['index', '-u', dirpath]
		if 'exclude_paths' in opts:
			for excluded in opts['exclude_paths']:
				args.append('--exclude', excluded)
		if 'exclude_rxs' in opts:
			for excluded in opts['exclude_rxs']:
				args.append('--exclude-rx', excluded)
		if 'one_file_system' in opts and opts['one_file_system']:
			args.append('--one-file-system')

		return self.run(args, callbacks)

	def save(self, dirpath, opts={}, callbacks={}):
		args = ['save', '-n', opts['name'], dirpath]
		return self.run(args, callbacks)

	def fuse(self, mountPath, callbacks={}):
		self.run(['fuse', mountPath], callbacks)

	def run(self, args, callbacks={}):
		env = {'BUP_FORCE_TTY': '2'}
		if self.dir is not None:
			env['BUP_DIR'] = self.dir

		if 'onprogress' in callbacks:
			args += ['--format', 'json']
			def onstderr(line):
				progress = None
				try:
					progress = json.loads(line)
				except ValueError, e:
					if 'onstatus' in callbacks:
						callbacks['onstatus'](line)
					else:
						print(line)
					return
				callbacks['onprogress'](progress)
			callbacks['stderr'] = onstderr

		# Start subprocess
		patched_cmd = os.path.dirname(__file__)+'/cmd/'+args[0]+'-cmd.py'
		if os.path.isfile(patched_cmd):
			args[0] = patched_cmd
			args.insert(0, sys.executable)
		else:
			args.insert(0, 'bup')

		proc = Popen(args, env=env, stdout=None, stderr=PIPE, universal_newlines=True)

		if "stderr" in callbacks:
			for line in unbuffered(proc, 'stderr'):
				callbacks["stderr"](line)
		elif "stdout" in callbacks:
			for line in unbuffered(proc, 'stdout'):
				callbacks["stdout"](line)

		if "onclose" in callbacks:
			callbacks["onclose"](proc.poll())
