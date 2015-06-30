import os
from base import FuseBase

#from ..sudo import sudo
try:
	from bups.sudo import sudo
except ImportError, e:
	from sudo import sudo

class FuseRoot(FuseBase):
	def __init__(self, cfg):
		FuseBase.__init__(self)

		self.cfg = cfg

	def mount(self, mount_path, parent_path=None):
		cfg = self.cfg

		if cfg.get("type", "") == "":
			return # Nothing to do

		FuseBase.mount(self, mount_path, parent_path)

		if os.path.ismount(mount_path):
			pass #raise RuntimeError("Filesystem already mounted")
		else:
			cmd = "mount -t "+cfg["type"]+" "+cfg["target"]+" "+mount_path+" -o "+cfg["options"]
			res = sudo(cmd)
			if res == 32:
				pass #raise RuntimeError("Filesystem busy")
			elif res != 0:
				raise RuntimeError("Could not mount "+cfg["type"]+" filesystem [#"+str(res)+"] (command: "+args+")")

	def unmount(self):
		if self.mount_path is None:
			raise RuntimeError("FUSE unmount failed: filesystem not mounted")

		cmd = "umount -l "+self.mount_path
		res = sudo(cmd)
		if res != 0:
			raise RuntimeError("Could not unmount "+self.cfg["type"]+" filesystem at "+self.mount_path+" [#"+str(res)+"]")

		os.rmdir(self.mount_path)

	def get_type(self):
		return self.cfg.get("type", "base")

	def get_inner_path(self):
		return self._get_inner_path(self.cfg.get("path", ""))