import subprocess
import os
import time

class FuseBase:
	def __init__(self):
		self.mount_path = None

	def mount(self, mount_path, parent_path=None):
		self.mount_path = mount_path

		if not os.path.exists(self.mount_path):
			os.makedirs(self.mount_path)

	def unmount(self):
		if self.mount_path is None:
			raise RuntimeError("FUSE unmount failed: filesystem not mounted")

		res = subprocess.call(["fusermount -u -z "+self.mount_path], shell=True)
		if res != 0:
			pass

		time.sleep(1)

		os.rmdir(self.mount_path)
		self.mount_path = None

	def get_type(self):
		return "base"

	def get_mount_path(self):
		return self.mount_path

	def get_inner_path(self):
		return self.get_mount_path()

	def _get_inner_path(self, path):
		if path.startswith("/"):
			path = path[1:]

		mount_path = self.get_mount_path()
		if path != "":
			mount_path = os.path.join(mount_path, path)
		return mount_path
