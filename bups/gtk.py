import sys
import os
import pwd
from subprocess import PIPE, Popen, call
from gi.repository import Gtk, GObject, Pango, Gdk, Gio, GLib
from manager import BupManager
import anacron
import threading
import config

GObject.threads_init() # Important: enable multi-threading support in GLib

class BackupWindow(Gtk.Window):
	def __init__(self, manager, parent=None):
		Gtk.Window.__init__(self, title="Backup")
		self.set_border_width(10)
		self.set_icon_name("drive-harddisk")

		if parent is not None:
			self.set_transient_for(parent)

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

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		self.close_button = Gtk.Button("Close")
		self.close_button.connect("clicked", self.on_close_clicked)
		hbox.pack_end(self.close_button, False, False, 0)

		self.manager = manager

	def backup(self):
		manager = self.manager

		def set_window_deletable(deletable):
			self.set_deletable(deletable)
			parent = self.get_transient_for()
			if parent is not None:
				parent.set_deletable(deletable)

			if not deletable:
				self.close_button.hide()
				self.resize(1, 1) # Make window as small as possible
			else:
				self.close_button.show()

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
			GLib.idle_add(set_window_deletable, True)
			GLib.idle_add(self.progressbar.set_fraction, 1)

		def onabord():
			GLib.idle_add(set_window_deletable, True)
			GLib.idle_add(self.set_label, "Backup canceled.", False)

		callbacks = {
			"onstatus": onstatus,
			"onprogress": onprogress,
			"onerror": onerror,
			"onfinish": onfinish,
			"onabord": onabord
		}

		self.set_label("Backup started...")

		# Lock window
		set_window_deletable(False)

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

	def on_close_clicked(self, btn):
		self.destroy()

class SettingsWindow(Gtk.Window):
	def __init__(self, parent):
		Gtk.Window.__init__(self, title="Settings")
		self.set_default_size(150, 100)
		self.set_transient_for(parent)
		self.set_modal(True)
		self.set_icon_name("drive-harddisk")

		self.cfg = parent.load_config()

		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.add(box)

		nb = Gtk.Notebook()
		box.add(nb)

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		vbox.set_border_width(10)
		nb.append_page(vbox, Gtk.Label("Destination"))

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

		# Samba share
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Backup path", xalign=0)
		self.path_prefix_entry = Gtk.Entry()
		self.path_prefix_entry.set_text(self.cfg["mount"]["path"])
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.path_prefix_entry, False, True, 0)

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

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		vbox.set_border_width(10)
		nb.append_page(vbox, Gtk.Label("Schedule"))

		# Anacron
		anacron_available = True
		anacron_job = None
		try:
			anacron_job = anacron.get_job("bups")
		except IOError, e:
			anacron_available = False
			print("ERR: could not read anacron config: "+str(e))

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Schedule backups", xalign=0)
		self.schedule_switch = Gtk.Switch()
		self.schedule_switch.set_active(anacron_job is not None)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.schedule_switch, False, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label("Interval (days)", xalign=0)
		period = 1
		if anacron_job is not None and "period" in anacron_job:
			period = int(anacron_job["period"])
		adjustment = Gtk.Adjustment(period, 1, 100, 1, 7, 0)
		self.schedule_period_spin = Gtk.SpinButton()
		self.schedule_period_spin.set_adjustment(adjustment)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.schedule_period_spin, False, True, 0)

		if not anacron_available:
			self.schedule_switch.set_sensitive(False)
			self.schedule_period_spin.set_sensitive(False)
			label = Gtk.Label("Could not read anacron config.\nPlease check that anacron is installed and that you can read "+anacron.config_file+".")
			vbox.add(label)

		# Buttons
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		hbox.set_border_width(10)
		box.add(hbox)
		button = Gtk.Button("About")
		button.connect("clicked", parent.on_about_clicked)
		hbox.pack_start(button, False, False, 0)
		button = Gtk.Button("Close")
		button.connect("clicked", self.on_close_clicked)
		hbox.pack_end(button, False, False, 0)

	def show_all(self):
		Gtk.Window.show_all(self)
		self.on_mount_type_changed(self.mount_type_combo)

	def on_close_clicked(self, btn):
		#self.response(Gtk.ResponseType.OK)
		#win.connect("delete-event", win.quit)
		self.hide()

	def on_mount_type_changed(self, combo):
		mount_type = self.get_mount_type()

		for t in self.mount_boxes:
			box = self.mount_boxes[t]
			if t == mount_type:
				box.show()
			else:
				box.hide()

		self.resize(1, 1) # Make window as smaller as possible

	def get_mount_type(self):
		mount_type_iter = self.mount_type_combo.get_active_iter()
		if mount_type_iter != None:
			model = self.mount_type_combo.get_model()
			return model[mount_type_iter][0]
		else:
			return ""

	def get_config(self):
		self.cfg["mount"]["type"] = self.get_mount_type()
		self.cfg["mount"]["path"] = self.path_prefix_entry.get_text()

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

	def get_anacron_config(self):
		if not self.schedule_switch.get_active():
			return None

		dirname = os.path.realpath(os.path.dirname(__file__))
		logfile = dirname+"/anacron-log.log"
		cmd = dirname+"/anacron-worker.py"
		cmd += " > "+logfile+" 2>&1"

		cfg = {
			"period": self.schedule_period_spin.get_value_as_int(),
			"delay": 15,
			"id": "bups",
			"command": cmd
		}

		return cfg


class BupWindow(Gtk.ApplicationWindow):
	def __init__(self, app):
		Gtk.Window.__init__(self, title="Bups", application=app)
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

		self.liststore = Gtk.ListStore(str, str)

		self.treeview = Gtk.TreeView(model=self.liststore)

		renderer_text = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn("Directory", renderer_text, text=0)
		column.set_sort_column_id(0)
		self.treeview.append_column(column)
		column = Gtk.TreeViewColumn("Name", renderer_text, text=1)
		column.set_sort_column_id(1)
		self.treeview.append_column(column)

		vbox.pack_start(self.treeview, True, True, 0)

		self.config = None
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
			i = 0
			for d in self.config["dirs"]:
				dir_data = self.normalize_dir(d)
				if dir_data["path"] == dirpath:
					del self.config["dirs"][i]
				i += 1
			self.save_config()

	def get_default_backup_name(self, dirpath):
		login = ''
		try:
			login = os.getlogin()
		except OSError:
			login = pwd.getpwuid(os.getuid())[0]
		return login+"-"+os.path.basename(dirpath).lower()

	def normalize_dir(self, dir_data):
		if type(dir_data) == str or type(dir_data) == unicode:
			dir_data = {
				"path": dir_data,
				"name": self.get_default_backup_name(dir_data)
			}
		return dir_data

	def add_dir(self, dirpath):
		self.config["dirs"].append({
			"path": dirpath,
			"name": self.get_default_backup_name(dirpath)
		})
		self.save_config()
		self.add_dir_ui(dirpath)

	def add_dir_ui(self, dir_data):
		dir_data = self.normalize_dir(dir_data)
		self.liststore.append([dir_data["path"], dir_data["name"]])

	def on_backup_clicked(self, btn):
		win = BackupWindow(self.manager, parent=self)
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
		def onabord():
			GLib.idle_add(dialog.destroy)

		dialog.show_all()

		callbacks = {
			"onready": onready,
			"onstatus": onstatus,
			"onabord": onabord
		}

		t = threading.Thread(target=self.manager.mount, args=(callbacks,))
		t.start()

	def on_settings_clicked(self, btn):
		win = SettingsWindow(self)
		win.connect("hide", self.on_settings_closed)

		win.show_all()

	def on_settings_closed(self, win):
		self.config = win.get_config()
		print("Config changed")
		self.save_config()

		new_cfg = win.get_anacron_config()
		win.destroy()

		try:
			current_cfg = anacron.get_job("bups")
		except IOError, e:
			current_cfg = None

		try:
			task = None
			if new_cfg is None and current_cfg is not None: # Remove config
				def remove_job():
					anacron.remove_job(current_cfg["id"])
				task = remove_job
			elif new_cfg is not None:
				cfg_changed = True
				if current_cfg is not None:
					cfg_changed = int(current_cfg["period"]) != int(new_cfg["period"])
				if cfg_changed: # Add/update config
					def update_job():
						anacron.update_job(new_cfg)
					task = update_job

			if task is not None: # Run task with a loading dialog
				def run_task(task, onexit):
					task()
					onexit()

				dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, "Updating configuration...")
				def onexit():
					GLib.idle_add(dialog.destroy)

				dialog.show_all()

				t = threading.Thread(target=run_task, args=(task,onexit))
				t.start()
		except IOError, e:
			print("ERR: could not update anacron config: "+str(e))
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.OK, "Could not update anacron config")
			dialog.format_secondary_text(str(e))
			dialog.run()
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
			self.config = config.read()
		return self.config

	def save_config(self):
		if self.config is None:
			print("INFO: save_config() called but no config set")
			return
		try:
			config.write(self.config)
		except IOError, e:
			print("ERR: could not update config: "+str(e))
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.OK, "Could not update config")
			dialog.format_secondary_text(str(e))
			dialog.run()
			dialog.destroy()

	def quit(self, *args):
		if self.manager.mounted:
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, "Unmounting filesystem...")

			def onstatus(status):
				GLib.idle_add(dialog.format_secondary_text, status)
				print(status)
			def onfinish(data):
				GLib.idle_add(dialog.destroy)
				#GLib.idle_add(Gtk.main_quit)

			dialog.show_all()

			callbacks = {
				"onfinish": onfinish,
				"onstatus": onstatus
			}

			t = threading.Thread(target=self.manager.unmount, args=(callbacks,))
			t.start()
		else:
			pass #Gtk.main_quit()

class BupApp(Gtk.Application):
	def __init__(self):
		Gtk.Application.__init__(self)

	def do_activate(self):
		win = BupWindow(self)
		win.connect("delete-event", win.quit)
		win.show_all()

	def do_startup(self):
		Gtk.Application.do_startup(self)