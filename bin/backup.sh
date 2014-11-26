#!/usr/bin/env bash

dirname=`dirname $0`
errlog="$dirname/backup.log"
source $dirname/mount.sh

backupDirs=("$@")
if [ $# = 0 ] ; then
	backupDirs=("${BACKUP_DIRS[@]}")
fi

autoSuspendMode=`gsettings get org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type`
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type blank

echo "" > "$errlog"

(
echo "# Mounting filesystem..."
echo 0
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
	bup index -u "$dir" 2>> "$errlog"
	echo "# Backing up $dir as $backupName (saving files)..."
	bup save -n "$backupName" "$dir" 2>> "$errlog"
done

if [ $ENABLE_NOTIFY = 1 ] ; then
	notify-send -i drive-harddisk "Backup" "Backup finished." 2>>/dev/null
fi

echo "# Unmounting filesystem..."
umountShare

echo "# Backup finished."
) | (
	while read output ; do
		if [[ "$output" == Saving* ]] ; then
			echo $output | awk '{print $2}' | sed s/%//
			echo "# $output"
		else
			echo $output
		fi
	done
) |
(zenity --progress \
	--title="Backup" \
	--window-icon=drive-harddisk \
	--text="Backup started..." \
	--no-cancel)

gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type $autoSuspendMode

errors=`cat "$errlog"`
if [ "$errors" != "" ] ; then
	zenity --error \
		--title="Backup" \
		--text="Could not backup files: some errors occured. Please see logs in $errlog"
fi