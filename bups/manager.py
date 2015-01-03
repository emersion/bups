import os
import time
import subprocess
import tempfile

from worker import BupWorker
from sudo import sudo

def noop(*args):
	pass

class BupManager:
	def __init__(self, cfg):
		self.config = cfg

		self.mountPath = tempfile.mkdtemp(prefix="bups-mnt-")
		self.fuseMountPath = tempfile.mkdtemp(prefix="bups-fuse-")

		self.bupPath = self.mountPath
		if "path" in cfg["mount"] and cfg["mount"]["path"]:
			self.bupPath = os.path.join(self.bupPath, cfg["mount"]["path"])

		self.mounted = False

		self.bup = BupWorker()

	def backup(self, callbacks={}):
		if not "onstatus" in callbacks:
			callbacks["onstatus"] = noop
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop
		if not "onprogress" in callbacks:
			callbacks["onprogress"] = noop
		if not "onfinish" in callbacks:
			callbacks["onfinish"] = noop
		if not "onabord" in callbacks:
			callbacks["onabord"] = noop

		ctx = {}

		def backupDir(dir_data):
			dirpath = dir_data["path"].encode("ascii")
			backupName = dir_data["name"].encode("ascii")
			excludePaths = [x.encode("ascii") for x in dir_data.get("exclude", [])]
			excludeRxs = [x.encode("ascii") for x in dir_data.get("excluderx", [])]

			ctx = {
				"path": dirpath,
				"name": backupName
			}

			def onprogress(data):
				return callbacks["onprogress"](data, ctx)

			callbacks["onstatus"]("Backing up "+backupName+": indexing files...", ctx)

			self.bup.index(dirpath, {
				"exclude_paths": excludePaths,
				"exclude_rxs": excludeRxs
			}, {
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

		callbacks["onstatus"]("Mounting filesystem...", ctx)
		if not self.bupMount(callbacks):
			callbacks["onabord"]({}, ctx)
			return

		callbacks["onstatus"]("Initializing bup...", ctx)
		try:
			self.bup.init()
		except Exception, e:
			callbacks["onerror"]("WARN: "+str(e)+"\n", ctx)

		for dir_data in cfg["dirs"]:
			backupDir(dir_data)

		callbacks["onstatus"]("Unmounting filesystem...", ctx)
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
		if not "onabord" in callbacks:
			callbacks["onabord"] = noop

		cfg = self.config

		callbacks["onstatus"]("Mounting filesystem...")
		if not self.bupMount(callbacks):
			callbacks["onabord"]()
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
		res = subprocess.call(["fusermount -u "+self.fuseMountPath], shell=True)
		if res != 0:
			pass

		time.sleep(1)

		os.rmdir(self.fuseMountPath)

		callbacks["onstatus"]("Unmounting filesystem...")
		self.bupUnmount(callbacks)

		self.mounted = False
		callbacks["onfinish"]({})

	def bupMount(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		cfg = self.config
		if cfg["mount"]["type"] == "": # Nothing to mount
			return True

		if not os.path.exists(self.mountPath):
			os.makedirs(self.mountPath)

		if os.path.ismount(self.mountPath):
			callbacks["onerror"]("WARN: filesystem already mounted", {})
		else:
			cmd = "mount -t "+cfg["mount"]["type"]+" "+cfg["mount"]["target"]+" "+self.mountPath+" -o "+cfg["mount"]["options"]
			res = sudo(cmd)
			if res == 32:
				callbacks["onerror"]("WARN: filesystem busy", {})
			elif res != 0:
				callbacks["onerror"]("ERR: Could not mount samba [#"+str(res)+"] (command: "+args+")", {})
				return False

		self.bup.set_dir(self.bupPath)

		return True

	def bupUnmount(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		cfg = self.config
		if cfg["mount"]["type"] == "": # Nothing to unmount
			os.rmdir(self.mountPath)
			return True

		cmd = "umount "+self.mountPath
		res = sudo(cmd)
		if res != 0:
			callbacks["onerror"]("WARN: could not unmount samba filesystem ["+str(res)+"]", {})
			return False

		os.rmdir(self.mountPath)