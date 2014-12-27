Bups
====

Simple GUI for [Bup](https://github.com/bup/bup), a very efficient backup system.

![165_bups](https://cloud.githubusercontent.com/assets/506932/5287192/65b80d76-7b2a-11e4-8f80-eafbfaf884cb.png)

# Purposes

I personaly use it to backup my files to a hard disk drive plugged into my ISP box (it's a Livebox).

Features:
* Multiple directories support
* Backup, with a nice progressbar
* Show current backups in your favorite file manager
* Backups on local filesystem or over Samba
* Backup scheduling

# How to use

Requires Python 2, GTK3.

You can install Bups with [PyPI](https://pypi.python.org/pypi/Bups) or [download the source](https://github.com/emersion/bups/archive/master.zip).

If you choose to install from PyPI, you can run Bups with `bups`. A launcher will be added to your apps menu.

If you downloaded the source, just run `bin/bups`. To install a launcher for the current user, run `bin/create-launcher.py`.

# Configuration

You can edit config with the GUI. You can also manually edit `app/config/config.json` if you downloaded the source.
