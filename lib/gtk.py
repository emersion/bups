#!/usr/bin/env python2

import sys
import os
from subprocess import PIPE, Popen, call
from gi.repository import Gtk, GObject, Pango, Gdk, Gio, GLib
from bupworker import BupWorker
from manager import BupManager
import threading
import json

class BackupWindow(Gtk.Window):
	def __init__(self, manager):
		Gtk.Window.__init__(self, title="Backup")
		self.set_border_width(10)
		self.set_icon_name("drive-harddisk")

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.add(vbox)

		self.label = Gtk.Label("Ready.", xalign=0)
		self.label.set_justify(Gtk.Justification.LEFT)
		vbox.pack_start(self.label, False, False, 0)

		self.progressbar = Gtk.ProgressBar()
		vbox.pack_start(self.progressbar, False, False, 0)

		self.textview = Gtk.TextView()
		#self.textview.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0, 0, 0))
		#self.textview.modify_text(Gtk.StateType.NORMAL, Gdk.Color(255, 255, 255))
		fontdesc = Pango.FontDescription("monospace")
		self.textview.modify_font(fontdesc)
		self.textview.set_editable(False)
		scroll = Gtk.ScrolledWindow()
		scroll.add(self.textview)
		exp = Gtk.Expander()
		exp.set_label("Details")
		exp.add(scroll)
		vbox.pack_start(exp, True, True, 0)

		self.manager = manager

	def backup(self):
		manager = self.manager

		def onstatus(status, ctx):
			GLib.idle_add(self.set_label, status)

		def onprogress(progress, ctx):
			#print("PROGRESS", progress)
			if "percentage" in progress:
				GLib.idle_add(self.progressbar.set_fraction, progress["percentage"]/100)

			lbl = "Backing up "+ctx["name"]+": "
			if progress["type"] == "index":
				lbl += "indexing files"
			elif progress["type"] == "save":
				lbl += "saving files"
			elif progress["type"] == "read_index":
				lbl += "reading indexes"
			else:
				return
			lbl += " "
			if "files_done" in progress:
				lbl += "("+str(progress["files_done"])
				if "files_total" in progress:
					lbl += "/"+str(progress["files_total"])
				lbl += " files"
			if "bytes_done" in progress:
				lbl += ", "+str(int(progress["bytes_done"]/1024))+"/"+str(int(progress["bytes_total"]/1024))+"k"
			if "remaining_time" in progress and progress["remaining_time"]:
				lbl += ", "+progress["remaining_time"]+" remaining"
			if "speed" in progress and progress["speed"]:
				lbl += ", "+progress["speed"]
			lbl += ")..."

			GLib.idle_add(self.set_label, lbl)

		def onerror(err, ctx):
			GLib.idle_add(self.append_log, err)

		def onfinish(data, ctx):
			GLib.idle_add(self.progressbar.set_fraction, 1)

		callbacks = {
			"onstatus": onstatus,
			"onprogress": onprogress,
			"onerror": onerror,
			"onfinish": onfinish
		}

		self.set_label("Backup started...")

		t = threading.Thread(target=manager.backup, args=(callbacks,))
		t.start()

	def set_label(self, txt, logLabel=True):
		if txt == "":
			return
		self.label.set_text(txt)

		if logLabel:
			self.append_log(txt+"\n")

	def append_log(self, txt):
		buf = self.textview.get_buffer()
		buf.insert(buf.get_end_iter(), txt)
		#buf.insert_at_cursor(txt)
		print(txt.strip())

class SettingsWindow(Gtk.Dialog):
	def __init__(self, parent):
		Gtk.Dialog.__init__(self, "Settings", parent, 0,
			(Gtk.STOCK_CLOSE, Gtk.ResponseType.OK))
		self.set_border_width(10)
		self.set_default_size(150, 100)

		self.cfg = parent.load_config()

		box = self.get_content_area()
		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		box.add(vbox)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Samba path", xalign=0)
		self.target_entry = Gtk.Entry()
		self.target_entry.set_text(self.cfg["mount"]["target"])
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.target_entry, False, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Samba options", xalign=0)
		self.options_entry = Gtk.Entry()
		self.options_entry.set_text(self.cfg["mount"]["options"])
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.options_entry, False, True, 0)

		GObject.threads_init() # Important: enable multi-threading support in GLib
		self.show_all()

	def get_config(self):
		self.cfg["mount"]["target"] = self.target_entry.get_text()
		self.cfg["mount"]["options"] = self.options_entry.get_text()
		return self.cfg

class BupWindow(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, title="Bups")
		self.set_default_size(600, 400)
		self.set_icon_name("drive-harddisk")

		# Menu
		menu = Gtk.Menu()
		item = Gtk.MenuItem("Backup now")
		item.connect("activate", self.on_backup_clicked)
		menu.append(item)
		item = Gtk.MenuItem("Show backups")
		item.connect("activate", self.on_mount_clicked)
		menu.append(item)
		item = Gtk.MenuItem("Settings")
		item.connect("activate", self.on_settings_clicked)
		menu.append(item)
		item = Gtk.MenuItem("About")
		item.connect("activate", self.on_about_clicked)
		menu.append(item)
		menu.show_all()
		def on_settings_pressed(widget, event):
			if event.type == Gdk.EventType.BUTTON_PRESS:
				menu.popup(None, None, None, None, event.button, event.time)
				return True

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.add(vbox)

		if hasattr(Gtk, "HeaderBar"):
			hb = Gtk.HeaderBar(title="Bups")
			hb.set_show_close_button(True)
			hb.set_subtitle("Bup manager")
			self.set_titlebar(hb)

			box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			Gtk.StyleContext.add_class(box.get_style_context(), "linked")

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-add-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.connect("clicked", self.on_add_clicked)
			box.add(button)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-remove-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.connect("clicked", self.on_remove_clicked)
			box.add(button)

			hb.pack_start(box)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="open-menu-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			#button.connect("clicked", self.on_settings_clicked)
			button.add(image)
			hb.pack_end(button)

			button.connect("button-press-event", on_settings_pressed)
		else:
			tb = Gtk.Toolbar()
			tb.set_style(Gtk.ToolbarStyle.ICONS)
			vbox.pack_start(tb, False, False, 0)

			button = Gtk.ToolButton(Gtk.STOCK_ADD)
			button.connect("clicked", self.on_add_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_REMOVE)
			button.connect("clicked", self.on_remove_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_PROPERTIES)
			def on_settings_clicked(btn):
				event = Gdk.EventButton()
				event.type = Gdk.EventType.BUTTON_PRESS
				event.time = 0
				event.button = 1
				on_settings_pressed(btn, event)
			button.connect("clicked", on_settings_clicked)
			tb.add(button)

		self.liststore = Gtk.ListStore(str)

		self.treeview = Gtk.TreeView(model=self.liststore)

		renderer_text = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn("Directory", renderer_text, text=0)
		column.set_sort_column_id(0)
		self.treeview.append_column(column)

		#self.add(self.treeview)
		vbox.pack_start(self.treeview, True, True, 0)

		self.config = None
		self.configPath = os.path.abspath("../config/config.json")
		self.load_config()
		for dirpath in self.config["dirs"]:
			self.add_dir_ui(dirpath)

		self.manager = BupManager(self.load_config())

	def on_add_clicked(self, btn):
		dialog = Gtk.FileChooserDialog("Please choose a directory", self,
			Gtk.FileChooserAction.SELECT_FOLDER,
			(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
			Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

		response = dialog.run()
		if response == Gtk.ResponseType.OK:
			dirpath = dialog.get_filename()
			print("Dir selected: " + dirpath)

			self.add_dir(dirpath)
		elif response == Gtk.ResponseType.CANCEL:
			print("Cancel clicked")

		dialog.destroy()

	def on_remove_clicked(self, btn):
		selection = self.treeview.get_selection()
		model, treeiter = selection.get_selected()
		if treeiter != None:
			dirpath = model[treeiter][0]
			print("Removing dir "+dirpath)

			model.remove(treeiter)
			self.config["dirs"].remove(dirpath)
			self.save_config()

	def add_dir(self, dirpath):
		self.config["dirs"].append(dirpath)
		self.save_config()
		self.add_dir_ui(dirpath)

	def add_dir_ui(self, dirpath):
		self.liststore.append([dirpath])

	def on_backup_clicked(self, btn):
		win = BackupWindow(self.manager)
		win.show_all()

		win.backup()

	def on_mount_clicked(self, btn):
		dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, "Mounting filesystem...")

		def open_mounted(data):
			call("xdg-open "+data["path"], shell=True)

		def onstatus(status):
			GLib.idle_add(dialog.format_secondary_text, status)
			print(status)
		def onready(data):
			GLib.idle_add(dialog.destroy)
			GLib.idle_add(open_mounted, data)

		dialog.show_all()

		callbacks = {
			"onready": onready,
			"onstatus": onstatus
		}

		t = threading.Thread(target=self.manager.mount, args=(callbacks,))
		t.start()

	def on_settings_clicked(self, btn):
		dialog = SettingsWindow(self)
		response = dialog.run()

		if response == Gtk.ResponseType.OK:
			self.config = dialog.get_config()
			print("Config changed")
			self.save_config()

		dialog.destroy()

	def on_about_clicked(self, btn):
		dialog = Gtk.AboutDialog()
		dialog.set_transient_for(self)
		dialog.set_title('Bups')
		dialog.set_name('Bups')
		dialog.set_program_name('Bups')
		dialog.set_version('0.1')
		dialog.set_authors(['Emersion'])
		dialog.set_comments('Bup user interface with SAMBA shares support.')
		dialog.set_website('https://github.com/emersion/bups')
		dialog.set_logo_icon_name('drive-harddisk')
		dialog.set_license('Distributed under the MIT license.\nhttp://opensource.org/licenses/MIT')
		dialog.run()
		dialog.destroy()

	def load_config(self):
		if self.config is None:
			f = open(self.configPath, 'r')
			self.config = json.load(f)
			f.close()
		return self.config

	def save_config(self):
		if self.config is None:
			print("INFO: save_config() called but no config set")
			return
		f = open(self.configPath, 'w')
		json.dump(self.config, f, indent=4)
		f.close()

	def quit(self, *args):
		if self.manager.mounted:
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, "Unmounting filesystem...")

			def onstatus(status):
				GLib.idle_add(dialog.format_secondary_text, status)
				print(status)
			def onfinish(data):
				GLib.idle_add(dialog.destroy)
				GLib.idle_add(Gtk.main_quit)

			dialog.show_all()
			
			callbacks = {
				"onfinish": onfinish,
				"onstatus": onstatus
			}

			t = threading.Thread(target=self.manager.unmount, args=(callbacks,))
			t.start()
		else:
			Gtk.main_quit()

win = BupWindow()
win.connect("delete-event", win.quit)
win.show_all()

Gtk.main()