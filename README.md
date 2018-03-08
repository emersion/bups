Bups
====

Simple GUI for [Bup](https://github.com/bup/bup), a very efficient backup system.

![Main window](https://cloud.githubusercontent.com/assets/506932/8412281/2b916e6e-1e89-11e5-9b78-dbb6c55367de.png)

# Purposes

I personaly use it to backup my files to a hard disk drive plugged into my ISP box (it's a Livebox).

Features:
* Multiple directories support
* Backup, with a nice progressbar
* Show current backups in your favorite file manager
* Backups on local filesystem or over Samba, SSH and [Google Drive](https://github.com/astrada/google-drive-ocamlfuse)
* Backup scheduling (using `systemd` or `anacron`)
* Exclude paths/patterns
* Restore backups

Changelog: https://github.com/emersion/bups/releases

# How to use

Requires Python 2, GTK 3 and Bup. Tested on Archlinux and elementary OS (so it should run on Ubuntu and Debian).

Installation:
* If you are running on a Debian-based system, you can install the `.deb` package from here: https://github.com/emersion/bups/releases
* If you are using Archlinux, install it from the AUR: https://aur.archlinux.org/packages/bups/
* For development, you can download the source:
  
  ```shell
  git clone https://github.com/emersion/bups.git
  cd bups
  bin/bups
  ```

When installed, you can start Bups by running `bups`. A launcher will also be added to your desktop's app menu.

# Configuration

You can edit config with the GUI. You can also manually edit `~/.config/bups/config.json`.

# Translating

The project is on Transifex: https://www.transifex.com/emersion/bups/

You can also email me `.po` files if you don't want to register on Transifex. Download the source and run `tools/makepot.sh` to generate `lang/messages.pot`.
