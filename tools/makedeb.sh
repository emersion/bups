#!/usr/bin/env bash

dirname=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
setup="python2 $dirname/../setup.py"

rm -rf "$dirname/../deb_dist"
$dirname/../tools/makemo.sh
$setup --command-packages=stdeb.command bdist_deb --no-autoreq
