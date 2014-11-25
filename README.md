bup-samba
=========

Simple scripts to use Bup over Samba

# Purposes

I personaly use these scripts to backup my files to a hard disk drive plugged into my Internet box (Livebox).

# How to use

From a terminal:
* Make a backup: `bin/backup.sh`
* Show backups: `bin/fuse.sh`

Launchers are available in `apps/`

# Configuration

All config is stored in `bin/mount.sh`:
```bash
BACKUP_DIRS=("/path/to/dir" "/path/to/another/dir") # Dirs to backup
HOST="livebox" # Samba hostname
SHARE="backups" # Samba share
OPTIONS="guest" # Samba options
NOTIFY=1 # Send a notification when making a backup
```
