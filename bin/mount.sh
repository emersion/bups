#!/usr/bin/bash

HOST="livebox"
SHARE="backups"
OPTIONS="guest"
MOUNT_PATH="mnt"

mkdir "$MOUNT_PATH" 2>>/dev/null
sudo mount -t cifs //$HOST/$SHARE "$MOUNT_PATH" -o $OPTIONS
echo $MOUNT_PATH

# Does not work
#gvfs-mount smb://$HOST/$SHARE
#gvfsDir=`mount | grep gvfs | cut -f 3 -d " "`
#mntDir=`ls $gvfsDir | grep smb-share:server=$HOST,share=$SHARE`
#echo $gvfsDir/$mntDir