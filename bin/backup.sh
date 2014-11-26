#!/usr/bin/env bash

(
dirname=`dirname $0`
source $dirname/mount.sh

backupDirs=("$@")
if [ $# = 0 ] ; then
	backupDirs=("${BACKUP_DIRS[@]}")
fi

echo "# Mounting filesystem..."
mountShare

echo "# Initializing Bup..."
bup init

if [ $ENABLE_NOTIFY = 1 ] ; then
	notify-send -i drive-harddisk "Backup" "Backup started..." 2>>/dev/null
fi

for dir in "${backupDirs[@]}" ; do
	backupName=$USER-`basename "$dir" | tr -d ' ' | tr '[:upper:]' '[:lower:]'`
	echo -e "${Cyan}Backing up $dir as $backupName...${Color_Off}"
	echo "# Backing up $dir as $backupName (indexing files)..."
	bup index -u "$dir"
	echo "# Backing up $dir as $backupName (saving files)..."
	bup save -n "$backupName" "$dir"
done

if [ $ENABLE_NOTIFY = 1 ] ; then
	notify-send -i drive-harddisk "Backup" "Backup finished." 2>>/dev/null
fi

echo "# Unmounting filesystem..."
umountShare

echo "# Backup finished."
) |
(zenity --progress \
	--title="Backup" \
	--window-icon=drive-harddisk \
	--text="Backup started..." \
	--pulsate 2>>/dev/null)
