#!/usr/bin/env bash

dirname=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

xgettext "$dirname/../bups/gtk.py" --output-dir="$dirname/../locale/" --language=Python
mv "$dirname/../locale/messages.po" "$dirname/../locale/messages.pot"