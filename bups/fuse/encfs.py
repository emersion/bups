import os
import subprocess
from base import FuseBase

class FuseEncfs(FuseBase):
	def __init__(self):
		FuseBase.__init__(self)

	def mount(self, mount_path, parent_path=None):
		if parent_path is None:
			raise ValueError("EncFS filesystem requires parent path")

		askpass = "/usr/lib/ssh/ssh-askpass"
		if not os.path.isfile(askpass):
			raise RuntimeError("Cannot find "+askpass)

		FuseBase.mount(self, mount_path)

		res = subprocess.call(["encfs --standard --extpass="+askpass+" "+parent_path+" "+mount_path], shell=True)
		if res != 0:
			raise RuntimeError("Cannot mount encfs filesystem [#"+str(res)+"]")

	def get_type(self):
		return "encfs"
