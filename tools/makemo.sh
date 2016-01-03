#!/usr/bin/env bash

dirname=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

for langdir in $(echo "$dirname/../locale/*/"); do
	msgfmt "$langdir/LC_MESSAGES/bups.po" -o "$langdir/LC_MESSAGES/bups.mo"
done
