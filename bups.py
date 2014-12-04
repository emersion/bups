#!/usr/bin/env python2

import sys
from gi.repository import Gtk
from lib.gtk import BupWindow
from lib.gtk import BupApp

app = BupApp()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
