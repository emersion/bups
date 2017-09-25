#!/usr/bin/env python2

import os
from distutils.core import setup

dirname = os.path.dirname(__file__)

version_file = open(os.path.join(dirname, 'bups', 'VERSION'))
__version__ = version_file.read().strip()

locale_files = []
for locale in os.listdir(os.path.join(dirname, 'locale')):
	locale_files.append(('/usr/share/locale/'+locale+'/LC_MESSAGES', ['locale/'+locale+'/LC_MESSAGES/bups.mo']))

setup(
	name="Bups",
	version=__version__,
	author="emersion",
	url="https://github.com/emersion/bups",
	description="Simple GUI for Bup, a very efficient backup system.",
	license="MIT",

	packages=["bups", "bups.fuse", "bups.scheduler"],
	package_dir={"bups": "bups"},
	package_data={"bups": ["config/*.json", "VERSION"]},
	data_files=[
		('/usr/share/applications', ['bin/bups.desktop'])
	] + locale_files,
	scripts=["bin/bups"],
)
