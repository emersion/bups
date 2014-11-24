#!/usr/bin/bash

echo "Mounting samba filesystem..."
mnt=`./mount.sh 2>>bup.log`
export BUP_DIR=$mnt

bupMnt="mnt-bup"

bup init

echo "Starting bup-fuse..."
mkdir $bupMnt 2>>/dev/null
bup fuse -f $bupMnt &
pid=$!

function cleanup {
	echo "Cleaning up..."
	fusermount -u $bupMnt
	sleep 1 # Wait for FUSE to stop preperly
	sudo umount $mnt
}
trap cleanup EXIT

sleep 1 # Wait for FUSE to start preperly
xdg-open "`pwd`/$bupMnt"

echo "Ready!"
wait $pid
