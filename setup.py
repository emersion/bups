#!/usr/bin/env python2

import os
from distutils.core import setup

version_file = open(os.path.join(os.path.dirname(__file__), 'VERSION'))
__version__ = version_file.read().strip()

setup(
	name="Bups",
	version=__version__,
	author="emersion",
	author_email="contact@emersion.fr",
	url="https://github.com/emersion/bups",
	description="Simple GUI for Bup, a very efficient backup system.",

	packages=["bups", "bups.worker", "bups.scheduler"],
	package_dir={"bups": "bups"},
	package_data={"bups": ["config/*.json"]},
	data_files=[
		('', ['VERSION']),
		('/usr/share/applications', ['bin/bups.desktop'])
	],
	scripts=["bin/bups"],
)