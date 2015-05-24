from base import FuseBase
import time

class FuseBup(FuseBase):
	def __init__(self, worker):
		FuseBase.__init__(self)

		self.bup = worker

	def mount(self, mount_path, parent_path=None):
		if parent_path is None and self.bup.get_dir() is None:
			raise ValueError("Bup FUSE filesystem requires parent path")

		FuseBase.mount(self, mount_path, parent_path)

		if parent_path is not None:
			self.bup.set_dir(parent_path)

		self.bup.init()

		self.bup.fuse(mount_path, {
			#"stdout": callbacks["onstatus"],
			#"stderr": callbacks["onstatus"]
		})

		time.sleep(1)

	def get_type(self):
		return "bup"