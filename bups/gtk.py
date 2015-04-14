import sys
import os
import pwd
from subprocess import PIPE, Popen, call
from gi.repository import Gtk, GObject, Pango, Gdk, Gio, GLib
from manager import BupManager
from scheduler import schedulers
from version import __version__
import threading
import config
import traceback
import gettext

GObject.threads_init() # Important: enable multi-threading support in GLib

# l10n
if gettext.find('bups', os.path.dirname(__file__)+'/../locale'):
	gettext.install('bups', os.path.dirname(__file__)+'/../locale')
else: # Try global translation
	gettext.install('bups')

class BackupWindow(Gtk.Window):
	def __init__(self, manager, parent=None):
		Gtk.Window.__init__(self, title=_("Backup"))
		self.set_border_width(10)
		self.set_icon_name("drive-harddisk")
		self.set_position(Gtk.WindowPosition.CENTER)

		if parent is not None:
			self.set_transient_for(parent)

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.add(vbox)

		self.label = Gtk.Label(_("Ready."), xalign=0)
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
		sw = Gtk.ScrolledWindow()
		sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
		sw.set_min_content_height(200)
		sw.add(self.textview)
		exp = Gtk.Expander()
		exp.set_label(_("Details"))
		exp.add(sw)
		vbox.pack_start(exp, True, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		self.close_button = Gtk.Button(_("Close"))
		self.close_button.connect("clicked", self.on_close_clicked)
		hbox.pack_end(self.close_button, False, False, 0)

		self.manager = manager

	def backup(self):
		manager = self.manager

		finished = False

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
			if finished:
				return

			#print("PROGRESS", progress)
			if "percentage" in progress:
				if type(progress["percentage"]) == int or type(progress["percentage"]) == float:
					GLib.idle_add(self.progressbar.set_fraction, progress["percentage"]/100)
				else:
					GLib.idle_add(self.progressbar.pulse)

			lbl = _("Backing up {name}: ").format(name=ctx["name"])

			if not "status" in progress:
				return

			if progress["status"] == "indexing":
				lbl += _("indexing files")
			elif progress["status"] == "saving":
				lbl += _("saving files")
			elif progress["status"] == "reading_index":
				lbl += _("reading indexes")
			else:
				return

			lbl += " ("

			if "files_done" in progress:
				lbl += str(progress["files_done"])
				if "files_total" in progress:
					lbl += "/"+str(progress["files_total"])
				lbl += " "+_("files")
			if "bytes_done" in progress:
				lbl += ", "+str(int(progress["bytes_done"]/1024))+"/"+str(int(progress["bytes_total"]/1024))+" "+_("KiB")
			if "remaining_time" in progress and progress["remaining_time"]:
				lbl += ", "+_("{remaining_time} remaining").format(remaining_time=progress["remaining_time"])
			if "speed" in progress and progress["speed"]:
				lbl += ", "+str(progress["speed"])+" "+_("KiB/s")
			if progress["status"] == "indexing":
				if "paths_per_sec" in progress:
					lbl += str(int(progress["paths_per_sec"]))+" "+_("paths/s")
				if "total_paths" in progress:
					lbl += ", "+str(progress["total_paths"])+" "+_("paths indexed")

			if lbl[-1] == "(":
				lbl = lbl[:-2]
			else:
				lbl += ")"
			lbl += "..."

			GLib.idle_add(self.set_label, lbl, False)

		def onerror(err, ctx):
			GLib.idle_add(self.append_log, err)

		def onfinish(data, ctx):
			GLib.idle_add(set_window_deletable, True)
			GLib.idle_add(self.progressbar.set_fraction, 1)
			finished = True

		def onabord():
			GLib.idle_add(set_window_deletable, True)
			GLib.idle_add(self.set_label, _("Backup canceled."), False)

		callbacks = {
			"onstatus": onstatus,
			"onprogress": onprogress,
			"onerror": onerror,
			"onfinish": onfinish,
			"onabord": onabord
		}

		self.set_label(_("Backup started..."))

		# Lock window
		set_window_deletable(False)

		def do_backup(manager, callbacks):
			try:
				return manager.backup(callbacks)
			except Exception, e:
				callbacks["onerror"](traceback.format_exc(), {})
				callbacks["onabord"]()

		t = threading.Thread(target=do_backup, args=(manager, callbacks))
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
		Gtk.Window.__init__(self, title=_("Settings"))
		self.set_default_size(150, 100)
		self.set_transient_for(parent)
		self.set_modal(True)
		self.set_icon_name("drive-harddisk")
		self.set_position(Gtk.WindowPosition.CENTER)

		self.cfg = parent.load_config()

		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		self.add(box)

		stack, nb = None, None
		if hasattr(Gtk, "Stack"): # Use Stack if available
			stack = Gtk.Stack()
			stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

			stack_switcher = Gtk.StackSwitcher()
			stack_switcher.set_stack(stack)
			stack_switcher.set_halign(Gtk.Align.CENTER)

			box.pack_start(stack_switcher, False, False, 0)
			box.pack_start(stack, True, True, 0)
		else:
			nb = Gtk.Notebook()
			box.add(nb)

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
		vbox.set_border_width(10)
		if stack is not None:
			stack.add_titled(vbox, "destination", _("Destination"))
		else:
			nb.append_page(vbox, Gtk.Label(_("Destination")))

		# Filesystem type
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label(_("Filesystem type"), xalign=0)

		mount_types = ["", "cifs"]
		mount_types_names = [_("Local"), _("SAMBA")]
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
		label = Gtk.Label(_("Hostname"), xalign=0)
		self.samba_host_entry = Gtk.Entry()
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.samba_host_entry, False, True, 0)

		# Samba share
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		samba_box.add(hbox)
		label = Gtk.Label(_("Samba share"), xalign=0)
		self.samba_share_entry = Gtk.Entry()
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.samba_share_entry, False, True, 0)

		# Login
		# TODO: not implemented
		self.samba_guest_check = Gtk.CheckButton(_("Anonymous login"))
		self.samba_guest_check.set_sensitive(False)
		self.samba_guest_check.set_active(True)
		samba_box.add(self.samba_guest_check)

		self.mount_boxes["cifs"] = samba_box

		# Samba share
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label(_("Backup path"), xalign=0)
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
		if stack is not None:
			stack.add_titled(vbox, "schedule", _("Schedule"))
		else:
			nb.append_page(vbox, Gtk.Label(_("Schedule")))

		# Schedulers
		i = 0
		job = None
		active_scheduler = 0 # By default, activate the first one
		for name in schedulers:
			s = schedulers[name]
			try:
				job = s.get_job("bups")
			except IOError, e:
				i += 1
				continue
			active_scheduler = i
			break

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label(_("Schedule backups"), xalign=0)
		self.schedule_switch = Gtk.Switch()
		self.schedule_switch.set_active(job is not None)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.schedule_switch, False, True, 0)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label(_("Scheduler"), xalign=0)
		schedulers_store = Gtk.ListStore(str, str, bool)
		available_schedulers_nbr = 0
		for name in schedulers:
			avail = schedulers[name].is_available()
			if avail:
				available_schedulers_nbr += 1
			schedulers_store.append([name, name, avail])
		self.scheduler_combo = Gtk.ComboBox.new_with_model(schedulers_store)
		renderer_text = Gtk.CellRendererText()
		self.scheduler_combo.pack_start(renderer_text, True)
		self.scheduler_combo.add_attribute(renderer_text, "text", 1)
		self.scheduler_combo.add_attribute(renderer_text, "sensitive", 2)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.scheduler_combo, False, True, 0)

		if available_schedulers_nbr > 0:
			self.scheduler_combo.set_active(active_scheduler)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		vbox.add(hbox)
		label = Gtk.Label(_("Interval (days)"), xalign=0)
		period = 1
		if job is not None and "period" in job:
			period = int(job["period"])
		adjustment = Gtk.Adjustment(period, 1, 100, 1, 7, 0)
		self.schedule_period_spin = Gtk.SpinButton()
		self.schedule_period_spin.set_adjustment(adjustment)
		hbox.pack_start(label, True, True, 0)
		hbox.pack_start(self.schedule_period_spin, False, True, 0)

		# if not anacron_available:
		# 	self.schedule_switch.set_sensitive(False)
		# 	self.schedule_period_spin.set_sensitive(False)
		# 	label = Gtk.Label("Could not read anacron config.\nPlease check that anacron is installed and that you can read "+anacron.config_file+".")
		# 	vbox.add(label)

		if available_schedulers_nbr == 0:
			self.schedule_switch.set_sensitive(False)
			self.schedule_period_spin.set_sensitive(False)
			label = Gtk.Label(_("No scheduler available. Please install one of:")+" " + ", ".join(schedulers.keys())+".")
			vbox.add(label)

		# Buttons
		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
		hbox.set_border_width(10)
		box.add(hbox)
		button = Gtk.Button(_("About"))
		button.connect("clicked", parent.on_about_clicked)
		hbox.pack_start(button, False, False, 0)
		button = Gtk.Button(_("Close"))
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

	def get_scheduler_name(self):
		scheduler_iter = self.scheduler_combo.get_active_iter()
		if scheduler_iter != None:
			model = self.scheduler_combo.get_model()
			return model[scheduler_iter][0]
		else:
			return ""

	def get_scheduler_config(self):
		if not self.schedule_switch.get_active():
			return None

		dirname = os.path.realpath(os.path.dirname(__file__))
		logfile = dirname+"/scheduler-log.log"
		cmd = dirname+"/scheduler_worker.py"
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
		self.set_default_size(800, 400)
		self.set_icon_name("drive-harddisk")
		self.set_position(Gtk.WindowPosition.CENTER)

		vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
		self.add(vbox)

		if hasattr(Gtk, "HeaderBar"): # Use HeaderBar if available
			hb = Gtk.HeaderBar(title="Bups")
			hb.set_show_close_button(True)
			hb.set_subtitle(_("Bup manager"))
			self.set_titlebar(hb)

			# Add/remove
			box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			Gtk.StyleContext.add_class(box.get_style_context(), "linked")

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-add-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Add a directory"))
			button.connect("clicked", self.on_add_clicked)
			box.add(button)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="list-remove-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Remove this directory"))
			button.connect("clicked", self.on_remove_clicked)
			box.add(button)

			if hasattr(Gtk, "Revealer"):
				button = Gtk.ToggleButton()
			else:
				button = Gtk.Button()
			icon = Gio.ThemedIcon(name="document-properties-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Properties"))
			button.connect("clicked", self.on_properties_clicked)
			box.add(button)
			self.sidebar_btn = button

			hb.pack_start(box)

			# Backup/browse
			box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
			Gtk.StyleContext.add_class(box.get_style_context(), "linked")

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="drive-harddisk-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Backup now"))
			button.connect("clicked", self.on_backup_clicked)
			box.add(button)

			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="document-open-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Browse backups"))
			button.connect("clicked", self.on_mount_clicked)
			box.add(button)

			hb.pack_start(box)

			# Settings
			button = Gtk.Button()
			icon = Gio.ThemedIcon(name="emblem-system-symbolic")
			image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.BUTTON)
			button.add(image)
			button.set_tooltip_text(_("Settings"))
			button.connect("clicked", self.on_settings_clicked)
			hb.pack_end(button)
		else: # Fallback to Toolbar if HeaderBar is not available
			tb = Gtk.Toolbar()
			tb.set_style(Gtk.ToolbarStyle.ICONS)
			vbox.pack_start(tb, False, False, 0)

			button = Gtk.ToolButton(Gtk.STOCK_ADD)
			button.set_tooltip_text(_("Add a directory"))
			button.connect("clicked", self.on_add_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_REMOVE)
			button.set_tooltip_text(_("Remove this directory"))
			button.connect("clicked", self.on_remove_clicked)
			tb.add(button)

			sep = Gtk.SeparatorToolItem()
			tb.add(sep)

			button = Gtk.ToolButton(Gtk.STOCK_HARDDISK)
			button.set_tooltip_text(_("Backup now"))
			button.connect("clicked", self.on_backup_clicked)
			tb.add(button)

			button = Gtk.ToolButton(Gtk.STOCK_OPEN)
			button.set_tooltip_text(_("Browse backups"))
			button.connect("clicked", self.on_mount_clicked)
			tb.add(button)

			sep = Gtk.SeparatorToolItem()
			sep.set_draw(False)
			sep.set_expand(True)
			tb.add(sep)

			button = Gtk.ToolButton(Gtk.STOCK_PROPERTIES)
			button.set_tooltip_text(_("Settings"))
			button.connect("clicked", self.on_settings_clicked)
			tb.add(button)

		self.liststore = Gtk.ListStore(str, str)

		self.treeview = Gtk.TreeView(model=self.liststore)

		renderer_text = Gtk.CellRendererText()
		column = Gtk.TreeViewColumn(_("Directory"), renderer_text, text=0)
		column.set_sort_column_id(0)
		self.treeview.append_column(column)

		renderer_text = Gtk.CellRendererText()
		renderer_text.set_property("editable", True)
		renderer_text.connect("edited", self.on_backup_name_edited)
		column = Gtk.TreeViewColumn(_("Name"), renderer_text, text=1)
		column.set_sort_column_id(1)
		self.treeview.append_column(column)

		hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
		vbox.pack_start(hbox, True, True, 0)

		scrolled = Gtk.ScrolledWindow()
		scrolled.add(self.treeview)

		hbox.pack_start(scrolled, True, True, 0)

		self.sidebar = None
		if hasattr(Gtk, "Revealer"): # Gtk.Revealer is available since GTK 3.10
			self.sidebar = Gtk.Revealer()
			self.sidebar.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)

			self.create_properties(self.sidebar)

			hbox.pack_start(self.sidebar, False, False, 0)

			selection = self.treeview.get_selection()
			selection.connect("changed", self.on_treeview_selection_changed)

		self.config = None
		self.load_config()
		for dirpath in self.config["dirs"]:
			self.add_dir_ui(dirpath)

		self.manager = BupManager(self.load_config())

	def create_properties(self, outer):
		sidebar_ctn = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
		outer.add(sidebar_ctn)

		sidebar_ctn.pack_start(Gtk.VSeparator(), False, False, 0)

		sidebar_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
		sidebar_vbox.set_border_width(10)
		sidebar_ctn.pack_start(sidebar_vbox, True, True, 0)

		sidebar_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		sidebar_vbox.add(sidebar_hbox)
		label = Gtk.Label(_("Backup name"), xalign=0)
		self.sidebar_name_entry = Gtk.Entry()
		sidebar_hbox.pack_start(label, True, True, 0)
		sidebar_hbox.pack_start(self.sidebar_name_entry, False, True, 0)

		sidebar_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		sidebar_vbox.add(sidebar_hbox)
		label = Gtk.Label(_("Exclude paths"), xalign=0)
		self.sidebar_exclude_entry = Gtk.Entry()
		sidebar_hbox.pack_start(label, True, True, 0)
		sidebar_hbox.pack_start(self.sidebar_exclude_entry, False, True, 0)

		sidebar_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		sidebar_vbox.add(sidebar_hbox)
		label = Gtk.Label(_("Exclude patterns"), xalign=0)
		self.sidebar_excluderx_entry = Gtk.Entry()
		sidebar_hbox.pack_start(label, True, True, 0)
		sidebar_hbox.pack_start(self.sidebar_excluderx_entry, False, True, 0)

		label = Gtk.Label()
		label.set_markup("<small>"+_("Enter a comma-separated list of paths and patterns to exclude.")+
			"\n<a href=\"https://github.com/bup/bup/blob/master/Documentation/bup-index.md\">"+_("Read the docs")+"</a></small>")
		sidebar_vbox.add(label)

		self.sidebar_onefilesystem_check = Gtk.CheckButton(_("Don't cross filesystem boundaries"))
		sidebar_vbox.add(self.sidebar_onefilesystem_check)

		sidebar_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
		sidebar_vbox.pack_end(sidebar_hbox, False, False, 0)
		button = Gtk.Button(_("Save"))
		if hasattr(Gtk, "STYLE_CLASS_SUGGESTED_ACTION"): # Since GTK 3.10
			button.get_style_context().add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
		button.connect("clicked", self.on_sidebar_save)
		sidebar_hbox.pack_end(button, False, False, 0)
		button = Gtk.Button(_("Cancel"))
		button.connect("clicked", self.on_sidebar_cancel)
		sidebar_hbox.pack_end(button, False, False, 0)

	def get_selected_row_index(self):
		selection = self.treeview.get_selection()
		model, treeiter = selection.get_selected()
		path = model[treeiter].path
		index = path.get_indices()[0]

		return index

	def show_sidebar(self):
		if type(self.sidebar) == Gtk.Revealer:
			self.sidebar.set_reveal_child(True)
			self.sidebar_btn.set_active(True)

	def hide_sidebar(self):
		if type(self.sidebar) == Gtk.Revealer:
			self.sidebar.set_reveal_child(False)
			self.sidebar_btn.set_active(False)
		if type(self.sidebar) == Gtk.Window:
			self.sidebar.close()
			self.sidebar = None

	def update_sidebar(self):
		index = self.get_selected_row_index()
		cfg = self.config["dirs"][index]

		self.sidebar_name_entry.set_text(cfg["name"])

		exclude = ""
		if "exclude" in cfg:
			exclude = ", ".join(cfg["exclude"])
		self.sidebar_exclude_entry.set_text(exclude)

		excluderx = ""
		if "excluderx" in cfg:
			excluderx = ", ".join(cfg["excluderx"])
		self.sidebar_excluderx_entry.set_text(excluderx)

		onefilesystem = cfg.get("onefilesystem", False)
		self.sidebar_onefilesystem_check.set_active(onefilesystem)

	def on_treeview_selection_changed(self, selection):
		if self.sidebar.get_reveal_child():
			self.update_sidebar()

	def on_properties_clicked(self, btn):
		if hasattr(Gtk, "Revealer") and type(self.sidebar) == Gtk.Revealer:
			if not self.sidebar_btn.get_active():
				self.hide_sidebar()
				return

			self.update_sidebar()
			self.show_sidebar()
		else:
			self.sidebar = Gtk.Window(title=_("Properties"))
			self.sidebar.set_position(Gtk.WindowPosition.CENTER)
			self.sidebar.set_transient_for(self)
			self.sidebar.set_modal(True)
			self.sidebar.set_resizable(False)

			self.create_properties(self.sidebar)
			self.update_sidebar()

			self.sidebar.show_all()

	def on_sidebar_cancel(self, btn):
		self.hide_sidebar()

	def on_sidebar_save(self, btn):
		index = self.get_selected_row_index()
		
		cfg = self.config["dirs"][index]

		cfg["name"] = self.sidebar_name_entry.get_text()

		exclude = self.sidebar_exclude_entry.get_text()
		cfg["exclude"] = [x.strip() for x in exclude.split(',')]
		if "" in cfg["exclude"]: cfg["exclude"].remove("")

		excluderx = self.sidebar_excluderx_entry.get_text()
		cfg["excluderx"] = [x.strip() for x in excluderx.split(',')]
		if "" in cfg["excluderx"]: cfg["excluderx"].remove("")

		cfg["onefilesystem"] = self.sidebar_onefilesystem_check.get_active()

		self.config["dirs"][index] = cfg
		self.save_config()

		self.hide_sidebar()

	def on_add_clicked(self, btn):
		dialog = Gtk.FileChooserDialog(_("Please choose a directory"), self,
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

			self.on_sidebar_cancel(None)

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

	def on_backup_name_edited(self, widget, path, text):
		self.config["dirs"][int(path)]["name"] = text
		self.save_config()
		self.liststore[path][1] = text

	def on_backup_clicked(self, btn):
		win = BackupWindow(self.manager, parent=self)
		win.show_all()

		win.backup()

	def on_mount_clicked(self, btn):
		dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, _("Mounting filesystem..."))

		def open_mounted(data):
			call("xdg-open "+data["path"], shell=True)

		def show_error(e):
			print("ERR: could not mount bup filesystem: "+str(e))
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.OK, _("Could not mount filesystem"))
			dialog.format_secondary_text(str(e))
			dialog.run()
			dialog.destroy()

		def onstatus(status):
			GLib.idle_add(dialog.format_secondary_text, status)
			print(status)
		def onready(data):
			GLib.idle_add(dialog.destroy)
			GLib.idle_add(open_mounted, data)
		def onerror(err):
			GLib.idle_add(show_error, err)
		def onabord():
			GLib.idle_add(dialog.destroy)

		dialog.show_all()

		callbacks = {
			"onready": onready,
			"onstatus": onstatus,
			"onerror": onerror,
			"onabord": onabord
		}

		def do_mount(manager, callbacks):
			try:
				manager.mount(callbacks)
			except Exception, e:
				callbacks["onabord"]()
				callbacks["onerror"](traceback.format_exc())

		t = threading.Thread(target=do_mount, args=(self.manager, callbacks))
		t.start()

	def on_settings_clicked(self, btn):
		win = SettingsWindow(self)
		win.connect("hide", self.on_settings_closed)

		win.show_all()

	def on_settings_closed(self, win):
		self.config = win.get_config()
		self.save_config()

		new_scheduler_name = win.get_scheduler_name()
		new_cfg = win.get_scheduler_config()
		win.destroy()

		for name in schedulers:
			try:
				current_scheduler_name = name
				current_cfg = schedulers[name].get_job("bups")
				break
			except IOError, e:
				current_cfg = None

		current_scheduler = schedulers[current_scheduler_name]
		new_scheduler = schedulers[new_scheduler_name]

		def remove_job():
			print("Removing scheduler job "+current_cfg["id"])
			current_scheduler.remove_job(current_cfg["id"])
		def update_job():
			print("Updating scheduler job "+new_cfg["id"])
			new_scheduler.update_job(new_cfg)
		def remove_update_job():
			if current_cfg is not None:
				remove_job()
			update_job()

		def show_error(e):
			print("ERR: could not update scheduler config: "+str(e))
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.OK, _("Could not update scheduler config"))
			dialog.format_secondary_text(str(e))
			dialog.run()
			dialog.destroy()

		task = None
		if new_cfg is None and current_cfg is not None: # Remove config
			task = remove_job
		elif new_cfg is not None:
			cfg_changed = True
			if current_scheduler_name != new_scheduler_name:
				task = remove_update_job
			else:
				if current_cfg is not None:
					cfg_changed = int(current_cfg["period"]) != int(new_cfg["period"])
				if cfg_changed: # Add/update config
					task = update_job

		if task is not None: # Run task with a loading dialog
			def run_task(task, onexit):
				try:
					task()
				except Exception, e:
					GLib.idle_add(show_error, e)
				onexit()

			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, _("Updating configuration..."))
			def onexit():
				GLib.idle_add(dialog.destroy)

			dialog.show_all()

			t = threading.Thread(target=run_task, args=(task,onexit))
			t.start()

	def on_about_clicked(self, btn):
		dialog = Gtk.AboutDialog()
		dialog.set_transient_for(self)
		dialog.set_title('Bups')
		dialog.set_name('Bups')
		dialog.set_program_name('Bups')
		dialog.set_version(__version__)
		dialog.set_authors(['Emersion'])
		dialog.set_comments(_('Simple GUI for Bup, a very efficient backup system.'))
		dialog.set_website('https://github.com/emersion/bups')
		dialog.set_logo_icon_name('drive-harddisk')
		dialog.set_license(_('Distributed under the MIT license.')+'\nhttp://opensource.org/licenses/MIT')
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
		
		print("Saving config")

		try:
			config.write(self.config)
		except IOError, e:
			print("ERR: could not update config: "+str(e))
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.OK, _("Could not update config"))
			dialog.format_secondary_text(str(e))
			dialog.run()
			dialog.destroy()

	def quit(self, *args):
		if self.manager.mounted:
			dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.INFO, 0, _("Unmounting filesystem..."))

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