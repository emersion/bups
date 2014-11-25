#!/usr/bin/bash

dirname=`dirname $0`

source $dirname/mount.sh

bupMnt="$dirname/mnt-bup"

bup init

echo "Starting bup-fuse..."
mkdir $bupMnt 2>>/dev/null
bup fuse -f $bupMnt &
pid=$!

function cleanup {
	echo "Cleaning up..."
	fusermount -u $bupMnt
	sleep 1 # Wait for FUSE to stop properly
	umountShare
}
trap cleanup EXIT

sleep 1 # Wait for FUSE to start properly
xdg-open "$bupMnt"

echo "Ready!"
wait $pid
