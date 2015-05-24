import os
import time
import subprocess
import tempfile

from worker import BupWorker
#from sudo import sudo
from fuse.root import FuseRoot
from fuse.bup import FuseBup
from fuse.google_drive import FuseGoogleDrive
from fuse.encfs import FuseEncfs

def noop(*args):
	pass

class BupManager:
	def __init__(self, cfg, sudo_worker = None):
		self.config = cfg
		self.sudo_worker = sudo_worker

		self.mountPath = tempfile.mkdtemp(prefix="bups-mnt-")
		self.fuseMountPath = tempfile.mkdtemp(prefix="bups-fuse-")

		self.bupPath = self.mountPath
		if cfg["mount"].get("path", "") != "":
			self.bupPath = os.path.join(self.bupPath, cfg["mount"]["path"])

		self.mounted = False

		self.bup = BupWorker()

		self.bup_mounter = None

		# FS parents
		mount_cfg = self.config["mount"]
		mount_type = mount_cfg.get("type", "")
		if mount_type == "":
			self.parents = []
		elif mount_type == "google_drive":
			self.parents = [FuseGoogleDrive(mount_cfg)]
		else:
			self.parents = [FuseRoot(mount_cfg)]

		if mount_cfg.get("encrypt", False):
			self.parents.append(FuseEncfs())

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
			def onstatus(line):
				return callbacks["onstatus"](line, ctx)

			callbacks["onstatus"]("Backing up "+backupName+": indexing files...", ctx)

			self.bup.index(dirpath, {
				"exclude_paths": excludePaths,
				"exclude_rxs": excludeRxs,
				"one_file_system": dir_data.get("onefilesystem", False)
			}, {
				"onprogress": onprogress,
				"onstatus": onstatus
			})

			callbacks["onstatus"]("Backing up "+backupName+": saving files...", ctx)

			self.bup.save(dirpath, {
				"name": backupName,
				"progress": True
			}, {
				"onprogress": onprogress,
				"onstatus": onstatus
			})

		cfg = self.config

		callbacks["onstatus"]("Mounting filesystem...", ctx)
		if not self.bupMount(callbacks):
			callbacks["onabord"]({}, ctx)
			return

		callbacks["onstatus"]("Initializing bup...", ctx)

		self.bup.init({
			"onstatus": lambda line: callbacks["onstatus"](line, ctx)
		})

		for dir_data in cfg["dirs"]:
			backupDir(dir_data)

		time.sleep(1)

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
		if not self.mount_parents({
			'onerror': lambda msg, ctx: callbacks["onerror"](msg)
		}):
			callbacks["onabord"]()
			return

		callbacks["onstatus"]("Initializing bup...")

		mounter = FuseBup(self.bup)
		mount_path = tempfile.mkdtemp(prefix="bups-bup-")
		try:
			mounter.mount(mount_path)
		except Exception, e:
			callbacks["onerror"]("WARN: "+str(e)+"\n")

		self.bup_mounter = mounter

		callbacks["onstatus"]('Bup fuse filesystem mounted.')
		self.mounted = True
		callbacks["onready"]({
			"path": mounter.get_inner_path()
		})

	def unmount(self, callbacks={}):
		if not "onstatus" in callbacks:
			callbacks["onstatus"] = noop
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop
		if not "onfinish" in callbacks:
			callbacks["onfinish"] = noop

		if self.bup_mounter is None:
			return

		callbacks["onstatus"]("Unmounting bup filesystem...")
		try:
			self.bup_mounter.unmount()
		except Exception, e:
			callbacks["onerror"]("WARN: "+str(e)+"\n")

		callbacks["onstatus"]("Unmounting filesystem...")
		self.unmount_parents({
			'onerror': lambda msg, ctx: callbacks["onerror"](msg)
		})

		self.mounted = False
		callbacks["onfinish"]({})

	def parents_need_sudo(self):
		for mounter in self.parents:
			if isinstance(mounter, FuseRoot):
				return True
		return False

	def mount_parents(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		if self.parents_need_sudo() and self.sudo_worker is not None:
			res = self.sudo_worker.proxy_command("mount", callbacks)
			if res["success"]:
				self.bup.set_dir(res["bup_path"])
			return res["success"]

		last_mount_path = None
		for mounter in self.parents:
			mount_path = tempfile.mkdtemp(prefix="bups-"+mounter.get_type()+"-")
			mounter.mount(mount_path, last_mount_path)
			last_mount_path = mounter.get_inner_path()

		self.bup.set_dir(last_mount_path)
		return True

	def unmount_parents(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		if self.parents_need_sudo() and self.sudo_worker is not None:
			return self.sudo_worker.proxy_command("unmount", callbacks)["success"]

		for mounter in reversed(self.parents):
			mounter.unmount()

		return True