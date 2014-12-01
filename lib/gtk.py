#!/usr/bin/env python2

import sys
import os
from subprocess import PIPE, Popen, call
from gi.repository import Gtk, GObject, Pango, Gdk, Gio, GLib
from bupworker import BupWorker
from manager import BupManager
import threading
import json

GObject.threads_init() # Important: enable multi-threading support in GLib

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

			GLib.idle_add(self.set_label, lbl, False)

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
		Gtk.Dialog.__init__(self, "Settings", parent)
		self.set_border_width(10)
		self.set_default_size(150, 100)

		self.cfg = parent.load_config()

		box = self.get_content_area()
		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		box.add(vbox)

		# Filesystem type
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Filesystem type", xalign=0)

		mount_types = ["", "cifs"]
		mount_types_names = ["Local", "SAMBA"]
		mount_type_store = Gtk.ListStore(str, str)
		i = 0
		for t in mount_types:
			mount_type_store.append([t, mount_types_names[i]])
			i += 1
		self.mount_type_combo = Gtk.ComboBox.new_with_model(mount_type_store)
		renderer_text = Gtk.CellRendererText()
		self.mount_type_combo.pack_start(renderer_text, True)
		self.mount_type_combo.add_attribute(renderer_text, "text", 1)
		self.mount_type_combo.set_active(mount_types.index(self.cfg["mount"]["type"]))
		self.mount_type_combo.connect("changed", self.on_mount_type_changed)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.mount_type_combo, False, True, 0)

		self.mount_boxes = {}

		# Samba
		samba_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		vbox.add(samba_box)
		# Samba hostname
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		samba_box.add(hbox)
		label = Gtk.Label("Hostname", xalign=0)
		self.samba_host_entry = Gtk.Entry()
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.samba_host_entry, False, True, 0)

		# Samba share
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		samba_box.add(hbox)
		label = Gtk.Label("Samba share", xalign=0)
		self.samba_share_entry = Gtk.Entry()
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.samba_share_entry, False, True, 0)

		# Login
		# TODO: not implemented
		self.samba_guest_check = Gtk.CheckButton("Anonymous login")
		self.samba_guest_check.set_sensitive(False)
		self.samba_guest_check.set_active(True)
		samba_box.add(self.samba_guest_check)

		self.mount_boxes["cifs"] = samba_box

		# Load mount settings
		if self.cfg["mount"]["type"] == "cifs": # Samba
			host = ""
			share = ""
			target = self.cfg["mount"]["target"]
			if target.startswith("//"):
				target = target[2:]
			host, share = target.split("/", 1)

			self.samba_host_entry.set_text(host)
			self.samba_share_entry.set_text(share)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		button = Gtk.Button("About")
		button.connect("clicked", parent.on_about_clicked)
		hbox.pack_start(button, False, False, 0)
		button = Gtk.Button("Close")
		button.connect("clicked", self.on_close_clicked)
		hbox.pack_end(button, False, False, 0)

		self.show_all()
		self.on_mount_type_changed(self.mount_type_combo)

	def on_close_clicked(self, btn):
		self.response(Gtk.ResponseType.OK)

	def on_mount_type_changed(self, combo):
		mount_type = self.get_mount_type()

		for t in self.mount_boxes:
			box = self.mount_boxes[t]
			if t == mount_type:
				box.show()
			else:
				box.hide()

	def get_mount_type(self):
		mount_type_iter = self.mount_type_combo.get_active_iter()
		if mount_type_iter != None:
			model = self.mount_type_combo.get_model()
			return model[mount_type_iter][0]
		else:
			return ""

	def get_config(self):
		self.cfg["mount"]["type"] = self.get_mount_type()

		if self.cfg["mount"]["type"] == "cifs": # Samba
			self.cfg["mount"]["target"] = "//"+self.samba_host_entry.get_text()+"/"+self.samba_share_entry.get_text()
			opts = ""
			if self.samba_guest_check.get_active():
				opts = "guest"
			self.cfg["mount"]["options"] = opts
		if self.cfg["mount"]["type"] == "": # No fs mounting
			self.cfg["mount"]["target"] = ""
			self.cfg["mount"]["options"] = ""

		return self.cfg

class BupWindow(Gtk.Window):
	def __init__(self):
		Gtk.Window.__init__(self, title="Bups")
		self.set_default_size(600, 400)
		self.set_icon_name("drive-harddisk")

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.add(vbox)

		if hasattr(Gtk, "HeaderBar"):
			hb = Gtk.HeaderBar(title="Bups")
			hb.set_show_close_button(True)
			hb.set_subtitle("Bup manager")
			self.set_titlebar(hb)

			# Add/remove
			box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			Gtk.StyleContext.add_class(box.get_style_context(), "linked")

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-add-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text("Add a directory")
			button.connect("clicked", self.on_add_clicked)
			box.add(button)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-remove-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text("Remove this directory")
			button.connect("clicked", self.on_remove_clicked)
			box.add(button)

			hb.pack_start(box)

			# Backup/browse
			box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			Gtk.StyleContext.add_class(box.get_style_context(), "linked")

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="drive-harddisk-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text("Backup now")
			button.connect("clicked", self.on_backup_clicked)
			box.add(button)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="document-open-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text("Browse backups")
			button.connect("clicked", self.on_mount_clicked)
			box.add(button)

			hb.pack_start(box)

			# Settings
			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="emblem-system-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text("Settings")
			button.connect("clicked", self.on_settings_clicked)
			hb.pack_end(button)
		else:
			tb = Gtk.Toolbar()
			tb.set_style(Gtk.ToolbarStyle.ICONS)
			vbox.pack_start(tb, False, False, 0)

			button = Gtk.ToolButton(Gtk.STOCK_ADD)
			button.set_tooltip_text("Add a directory")
			button.connect("clicked", self.on_add_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_REMOVE)
			button.set_tooltip_text("Remove this directory")
			button.connect("clicked", self.on_remove_clicked)
			tb.add(button)

			sep = Gtk.SeparatorToolItem()
			tb.add(sep)

			button = Gtk.ToolButton(Gtk.STOCK_HARDDISK)
			button.set_tooltip_text("Backup now")
			button.connect("clicked", self.on_backup_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_OPEN)
			button.set_tooltip_text("Browse backups")
			button.connect("clicked", self.on_mount_clicked)
			tb.add(button)

			sep = Gtk.SeparatorToolItem()
			sep.set_draw(False)
			sep.set_expand(True)
			tb.add(sep)

			button = Gtk.ToolButton(Gtk.STOCK_PROPERTIES)
			button.set_tooltip_text("Settings")
			button.connect("clicked", self.on_settings_clicked)
			tb.add(button)

		self.liststore = Gtk.ListStore(str)

		self.treeview = Gtk.TreeView(model=self.liststore)

		renderer_text = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn("Directory", renderer_text, text=0)
		column.set_sort_column_id(0)
		self.treeview.append_column(column)

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