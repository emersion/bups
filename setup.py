from distutils.core import setup

setup(
	name="Bups",
	version="0.1.0",
	author="emersion",
	url="https://github.com/emersion/bups",
	description="Simple GUI for Bup, a very efficient backup system.",

	packages=["app"],
	include_package_data=True,
	install_requires=[]
)