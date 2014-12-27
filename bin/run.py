#!/usr/bin/env python2

import sys
sys.path.append('..')

from gi.repository import Gtk
from app.gtk import BupWindow
from app.gtk import BupApp

app = BupApp()
exit_status = app.run(sys.argv)
sys.exit(exit_status)
