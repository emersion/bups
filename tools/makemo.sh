#!/usr/bin/env bash

dirname=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

msgfmt "$dirname/../locale/fr/LC_MESSAGES/bups.po" -o "$dirname/../locale/fr/LC_MESSAGES/bups.mo"