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

Just run `bin/bups`.

Requires Python 2, GTK3.

Launchers are available in `launchers/`. To install a launcher for the current user, run `bin/create-launcher.py`.

# Configuration

You can edit config with the GUI. You can also manually edit `app/config/config.json`.
