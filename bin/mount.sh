#!/usr/bin/bash

HOST="livebox"
SHARE="backups"
OPTIONS="guest"
MOUNT_PATH="mnt"

echo "Mounting samba filesystem..."
mkdir "$MOUNT_PATH" 2>>/dev/null
sudo mount -t cifs //$HOST/$SHARE $MOUNT_PATH -o $OPTIONS

function umountShare {
	echo "Unmounting samba filesystem..."
	sudo umount $MOUNT_PATH
}

export BUP_DIR=$MOUNT_PATH

# Does not work
#gvfs-mount smb://$HOST/$SHARE
#gvfsDir=`mount | grep gvfs | cut -f 3 -d " "`
#mntDir=`ls $gvfsDir | grep smb-share:server=$HOST,share=$SHARE`
#echo $gvfsDir/$mntDir