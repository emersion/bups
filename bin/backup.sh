#!/usr/bin/bash

echo "Mounting samba filesystem..."
mnt=`./mount.sh 2>>bup.log`
export BUP_DIR=$mnt

bup init

for dir in "$@" ; do
	dir=$(readlink -f "$dir")
	backupName=$USER-`basename "$dir" | tr -d ' ' | tr '[:upper:]' '[:lower:]'`
	echo "Backing up $dir as $backupName..."
	bup index "$dir"
	bup save -n "$backupName" "$dir"
done

sudo umount $mnt