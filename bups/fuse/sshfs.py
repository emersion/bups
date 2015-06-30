import os
import subprocess
from base import FuseBase

class FuseSshfs(FuseBase):
	def __init__(self, cfg):
		FuseBase.__init__(self)

		self.target = cfg["target"]
		self.path = cfg.get("path", "")

	def mount(self, mount_path, parent_path=None):
		FuseBase.mount(self, mount_path, parent_path)

		res = subprocess.call(["sshfs "+self.target+":"+self.path+" "+mount_path], shell=True)
		if res != 0:
			raise RuntimeError("Cannot mount sshfs filesystem [#"+str(res)+"]")

	def get_type(self):
		return "sshfs"