import os
import time
import subprocess
import tempfile
import re

from worker import BupWorker
#from sudo import sudo
from fuse.root import FuseRoot
from fuse.bup import FuseBup
from fuse.sshfs import FuseSshfs
from fuse.google_drive import FuseGoogleDrive
from fuse.encfs import FuseEncfs

def noop(*args):
	pass

class BupManager:
	def __init__(self, cfg, sudo_worker = None):
		self.config = cfg
		self.sudo_worker = sudo_worker

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
		elif mount_type == "sshfs":
			self.parents = [FuseSshfs(mount_cfg)]
		else:
			self.parents = [FuseRoot(mount_cfg)]

		if mount_cfg.get("encrypt", False):
			self.parents.append(FuseEncfs())

	def backup(self, callbacks={}):
		callbacks_names = ["onstatus", "onerror", "onprogress", "onfinish", "onabord"]
		for name in callbacks_names:
			if not name in callbacks:
				callbacks[name] = noop

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

			def status2progress(line):
				m = re.search("Indexing:\s*(\d+)((?:,\s*done)?)\s*\((\d+) paths/s\)", line)
				if m is not None:
					percentage = None
					if m.group(2) != "":
						percentage = 100
					return {
						'status': 'indexing',
						'percentage': percentage,
						'total_paths': int(m.group(1)),
						'paths_per_sec': int(m.group(3))
					}

				m = re.search("Reading index:\s*(\d+)((?:,\s*done)?)", line)
				if m is not None:
					percentage = None
					if m.group(2) != "":
						percentage = 100
					return {
						'status': 'reading_index',
						'percentage': percentage,
						'files_done': int(m.group(1))
					}

				m = re.search("Saving:\s*([\d.]+)%\s*\((\d+)/(\d+)k, (\d+)/(\d+) files\)", line)
				if m is not None:
					return {
						'status': 'saving',
						'percentage': float(m.group(1)),
						'bytes_done': int(m.group(2)),
						'bytes_total': int(m.group(3)),
						'files_done': int(m.group(4)),
						'files_total': int(m.group(5))
					}

				return None

			def onprogress(data):
				return callbacks["onprogress"](data, ctx)
			def onstatus(line):
				progress = status2progress(line)
				if progress is not None:
					return callbacks["onprogress"](progress, ctx)

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
		if not self.mount_parents(callbacks):
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
		self.unmount_parents(callbacks)

		callbacks["onstatus"]('Backup finished.', ctx)
		callbacks["onfinish"]({}, ctx)

	def restore(self, opts, callbacks={}):
		callbacks_names = ["onstatus", "onerror", "onprogress", "onfinish", "onabord"]
		for name in callbacks_names:
			if not name in callbacks:
				callbacks[name] = noop

		callbacks["onstatus"]("Mounting filesystem...")
		if not self.mount_parents(callbacks):
			callbacks["onabord"]()
			return

		from_path = opts.get("from").encode("ascii")
		to_path = opts.get("to").encode("ascii")

		callbacks["onstatus"]("Restoring "+from_path+" to "+to_path+"...")

		self.bup.restore(from_path, to_path, callbacks)

		time.sleep(1)

		callbacks["onstatus"]("Unmounting filesystem...")
		self.unmount_parents(callbacks)

		callbacks["onstatus"]("Restoration finished.")
		callbacks["onfinish"]()

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

	def mount_log(self, msg):
		if self.sudo_worker is not None:
			return
		print(msg)

	def mount_parents(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		if self.parents_need_sudo() and self.sudo_worker is not None:
			res = self.sudo_worker.proxy_command("mount", callbacks)
			if res["success"]:
				self.bup.set_dir(res["bup_path"])
			return res["success"]

		mount_cfg = self.config["mount"]
		last_mount_path = self.bup.get_default_dir()
		if mount_cfg.get("type", "") == "" and mount_cfg.get("path", "") != "":
			last_mount_path = os.path.expanduser(mount_cfg["path"])

		for mounter in self.parents:
			mount_path = tempfile.mkdtemp(prefix="bups-"+mounter.get_type()+"-")

			self.mount_log("Mounting "+mounter.get_type()+" on "+mount_path)

			try:
				mounter.mount(mount_path, last_mount_path)
			except Exception, e:
				callbacks["onerror"]("ERR: "+str(e)+"\n", {})
				return False
			last_mount_path = mounter.get_inner_path()

		self.mount_log("Backup dir is "+last_mount_path)

		self.bup.set_dir(last_mount_path)
		return True

	def unmount_parents(self, callbacks={}):
		if not "onerror" in callbacks:
			callbacks["onerror"] = noop

		if self.parents_need_sudo() and self.sudo_worker is not None:
			return self.sudo_worker.proxy_command("unmount", callbacks)["success"]

		for mounter in reversed(self.parents):
			self.mount_log("Unmounting "+mounter.get_type()+" on "+mounter.get_mount_path())

			try:
				mounter.unmount()
			except Exception, e:
				callbacks["onerror"]("ERR: "+str(e)+"\n", {})
				return False

		return True
