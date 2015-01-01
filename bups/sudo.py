import os
import subprocess

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