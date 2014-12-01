Bups
====

Simple GUI for [Bup](https://github.com/bup/bup), a very efficient backup system.

![161_bups](https://cloud.githubusercontent.com/assets/506932/5239177/bb45c4a4-78d7-11e4-9571-3495a0daf0e0.png)

![163_settings](https://cloud.githubusercontent.com/assets/506932/5250462/839b2fa2-798c-11e4-8231-1cf9353f9c61.png)

# Purposes

I personaly use it to backup my files to a hard disk drive plugged into my ISP box (it's a Livebox).

Features:
* Multiple directories support
* Backup, with a nice progressbar
* Show current backups in your favorite file manager
* Backups on local filesystem or over Samba

# How to use

Just run `lib/gtk.py`.

Requires Python 2, GTK3.

Launchers are available in `apps/`

# Configuration

You can edit config with the GUI. You can also manually edit `config/config.json`.

# Old shell scripts

From a terminal:
* Make a backup: `bin/backup.sh`
* Show backups: `bin/fuse.sh`

All config is stored in `bin/mount.sh`:
```bash
BACKUP_DIRS=("/path/to/dir" "/path/to/another/dir") # Dirs to backup
HOST="livebox" # Samba hostname
SHARE="backups" # Samba share
OPTIONS="guest" # Samba options
ENABLE_NOTIFY=1 # Send a notification when making a backup
```
