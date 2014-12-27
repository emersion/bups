#!/usr/bin/env python2

import os
import sys
import stat

if not "HOME" in os.environ:
	print("$HOME is not set")
	sys.exit(1)

dest_path = os.environ["HOME"]+"/.local/share/applications/bups.desktop"
exec_path = os.path.realpath(os.path.dirname(__file__)+"/run.py")
launcher = """[Desktop Entry]
Name=Bups
Exec=%s
Icon=drive-harddisk
Terminal=false
Type=Application
Categories=Utility;Archiving;
""" % exec_path

if not os.path.exists(os.path.dirname(dest_path)):
	os.makedirs(os.path.dirname(dest_path))

f = open(dest_path, 'w')
f.write(launcher)
f.close()

# chmod +x
st = os.stat(dest_path)
os.chmod(dest_path, st.st_mode | stat.S_IXUSR)

print("Launcher successfully installed at "+dest_path)
