#!/usr/bin/env python2

from distutils.core import setup
from bups.version import __version__

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
	data_files=[('/usr/share/applications', ['bin/bups.desktop'])],
	scripts=["bin/bups"],
)