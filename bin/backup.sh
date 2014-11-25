#!/usr/bin/bash

source mount.sh

bup init

for dir in "$@" ; do
	dir=$(readlink -f "$dir")
	backupName=$USER-`basename "$dir" | tr -d ' ' | tr '[:upper:]' '[:lower:]'`
	echo "Backing up $dir as $backupName..."
	bup index "$dir"
	bup save -n "$backupName" "$dir"
done

umountShare