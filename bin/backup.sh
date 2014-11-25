#!/usr/bin/bash

dirname=`dirname $0`

source $dirname/mount.sh

backupDirs=("$@")
if [ $# = 0 ] ; then
	backupDirs=("$BACKUP_DIRS")
fi

bup init

if [ $NOTIFY = 1 ] ; then
	notify-send -i drive-harddisk "Backup" "Backup started..." 2>>/dev/null
fi

for dir in "$backupDirs" ; do
	backupName=$USER-`basename "$dir" | tr -d ' ' | tr '[:upper:]' '[:lower:]'`
	echo -e "${Cyan}Backing up $dir as $backupName...${Color_Off}"
	bup index "$dir"
	bup save -n "$backupName" "$dir"
done

if [ $NOTIFY = 1 ] ; then
	notify-send -i drive-harddisk "Backup" "Backup finished." 2>>/dev/null
fi

umountShare