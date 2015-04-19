import os
import subprocess
import json
import config

def command_exists(cmd):
	devnull = open(os.devnull, 'wb')
	rc = subprocess.call(['which', cmd], stdout=devnull, stderr=devnull)
	return (rc == 0)

def get_sudo(cmd):
	if type(cmd) == list:
		cmd = " && ".join(cmd)

	if os.geteuid() != 0:
		if "DISPLAY" in os.environ:
			if command_exists("pkexec"):
				sudo = "pkexec sh -c"
			elif command_exists("gksu"):
				sudo = "gksu"
			elif "SSH_ASKPASS" in os.environ:
				sudo = os.environ["SSH_ASKPASS"]+" | sudo -S sh -c"
			else:
				raise Exception("Could not find graphical sudo executable")
		else:
			sudo = "sudo sh -c"
		cmd = sudo+" \""+cmd+"\""
	return cmd

def sudo(cmd):
	return subprocess.call(get_sudo(cmd), shell=True)

class SudoQueue:
	def __init__(self):
		self.queue = []
	
	def append(self, cmd):
		self.queue.append(cmd)

	def execute(self):
		return sudo(self.queue)

	def reset(self):
		self.queue = []

class Worker:
	def __init__(self):
		self.proc = None

	def start(self):
		dirname = os.path.realpath(os.path.dirname(__file__))
		cmd = dirname+"/sudo_worker.py "+config.file_path()
		self.proc = subprocess.Popen(get_sudo(cmd), shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

	def send_command(self, cmd):
		if self.proc is None or self.proc.returncode is not None:
			# Process has not started/has terminated
			self.start()

		print('Send command', cmd)
		self.proc.stdin.write(cmd+"\n")
		self.proc.stdin.flush()
		json_res = self.proc.stdout.readline().strip()
		print('Got response', json_res)

		try:
			res = json.loads(json_res)
		except ValueError, e:
			res = {
				"success": False,
				"output": json_res
			}

		return res

	def proxy_command(self, cmd, callbacks):
		res = self.send_command(cmd)

		if res["output"] != "":
			callbacks["onerror"](res["output"], {})

		return res
