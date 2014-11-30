import os
import time
from subprocess import call
from bupworker import BupWorker

def noop(*args):
	pass

class BupManager:
	def __init__(self, cfg):
		self.config = cfg

		self.mountPath = os.path.abspath("mnt")
		self.fuseMountPath = os.path.abspath("mnt-bup")
		#self.sudoCmd = "sudo sh -c"
		self.sudoCmd = "gksu"

		self.mounted = False

	def backup(self, callbacks={}):
		if not "onstatus" in callbacks:
			callbacks["onstatus"] = noop
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop
		if not "onprogress" in callbacks:
			callbacks["onprogress"] = noop
		if not "onfinish" in callbacks:
			callbacks["onfinish"] = noop

		ctx = {}

		def backupDir(dirpath):
			backupName = os.getlogin()+"-"+os.path.basename(dirpath).lower()

			ctx = {
				"path": dirpath,
				"name": backupName
			}

			def onprogress(data):
				return callbacks["onprogress"](data, ctx)

			callbacks["onstatus"]("Backing up "+backupName+": indexing files...", ctx)

			self.bup.index(dirpath, {}, {
				"onread": lambda line: None,
				"onprogress": onprogress
			})

			callbacks["onstatus"]("Backing up "+backupName+": saving files...", ctx)

			self.bup.save(dirpath, {
				"name": backupName,
				"progress": True
			}, {
				"onprogress": onprogress
			})

		cfg = self.config
		self.bup = BupWorker(self.mountPath)

		callbacks["onstatus"]("Mounting samba filesystem...", ctx)
		if not self.bupMount(callbacks):
			return

		callbacks["onstatus"]("Initializing bup...", ctx)
		try:
			self.bup.init()
		except Exception, e:
			callbacks["onerror"]("WARN: "+str(e)+"\n", ctx)

		for dirpath in cfg["dirs"]:
			backupDir(dirpath.encode('ascii'))

		callbacks["onstatus"]("Unmounting samba filesystem...", ctx)
		self.bupUnmount(callbacks)

		callbacks["onstatus"]('Backup finished.', ctx)
		callbacks["onfinish"]({}, ctx)

	def mount(self, callbacks={}):
		if not "onstatus" in callbacks:
			callbacks["onstatus"] = noop
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop
		if not "onready" in callbacks:
			callbacks["onready"] = noop

		cfg = self.config
		self.bup = BupWorker(self.mountPath)

		callbacks["onstatus"]("Mounting samba filesystem...")
		if not self.bupMount(callbacks):
			return

		callbacks["onstatus"]("Initializing bup...")
		try:
			self.bup.init()
		except Exception, e:
			callbacks["onerror"]("WARN: "+str(e)+"\n")

		if not os.path.exists(self.fuseMountPath):
			os.makedirs(self.fuseMountPath)

		self.bup.fuse(self.fuseMountPath, {
			"stdout": callbacks["onstatus"],
			"stderr": callbacks["onstatus"]
		})

		time.sleep(1)

		callbacks["onstatus"]('Bup fuse filesystem mounted.')
		self.mounted = True
		callbacks["onready"]({
			"path": self.fuseMountPath
		})

	def unmount(self, callbacks={}):
		if not "onstatus" in callbacks:
			callbacks["onstatus"] = noop
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop
		if not "onfinish" in callbacks:
			callbacks["onfinish"] = noop

		callbacks["onstatus"]("Unmounting fuse filesystem...")
		res = call(["fusermount -u "+self.fuseMountPath], shell=True)
		if res != 0:
			pass

		time.sleep(1)

		callbacks["onstatus"]("Unmounting samba filesystem...")
		self.bupUnmount(callbacks)

		self.mounted = False
		callbacks["onfinish"]({})

	def bupMount(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		cfg = self.config

		if not os.path.exists(self.mountPath):
			os.makedirs(self.mountPath)

		args = "mount -t "+cfg["mount"]["type"]+" "+cfg["mount"]["target"]+" "+self.mountPath+" -o "+cfg["mount"]["options"]
		res = call([self.sudoCmd+" \""+args+"\""], shell=True)
		if res == 32:
			callbacks["onerror"]("WARN: samba filesystem busy", {})
		elif res != 0:
			callbacks["onerror"]("ERR: Could not mount samba ["+str(res)+"]", {})
			return False

		return True

	def bupUnmount(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		res = call([self.sudoCmd+" \"umount "+self.mountPath+"\""], shell=True)
		if res != 0:
			callbacks["onerror"]("WARN: could not unmount samba filesystem ["+str(res)+"]", {})
			return False