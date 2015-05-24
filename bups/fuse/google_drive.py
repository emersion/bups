import os
import subprocess
from base import FuseBase

class FuseGoogleDrive(FuseBase):
	def __init__(self, cfg):
		FuseBase.__init__(self)
		self.cfg = cfg

	def mount(self, mount_path, parent_path=None):
		FuseBase.mount(self, mount_path, parent_path)

		res = subprocess.call(["google-drive-ocamlfuse -skiptrash "+mount_path], shell=True)
		if res != 0:
			raise RuntimeError("Cannot mount google_drive filesystem [#"+str(res)+"]")

	def get_type(self):
		return "google_drive"

	def get_inner_path(self):
		mount_path = self.mount_path
		if self.cfg.get("path", "") != "":
			mount_path = os.path.join(mount_path, self.cfg["path"])
		return mount_path