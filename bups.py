#!/usr/bin/env python2

from gi.repository import Gtk
from lib.gtk import BupWindow

win = BupWindow()
win.connect("delete-event", win.quit)
win.show_all()

Gtk.main()