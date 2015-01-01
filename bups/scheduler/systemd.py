import os
import io
import ConfigParser
import subprocess
import tempfile
from ..sudo import SudoQueue

config_dir = "/etc/systemd/system"
sudo_queue = SudoQueue()

def is_available():
	return os.path.exists(config_dir)

def parse_period(time_str):
	return "7"

def new_config():
	config = ConfigParser.RawConfigParser()
	config.optionxform = str
	return config

def parse_config(timer_cfg):
	config = new_config()
	config.readfp(io.BytesIO(timer_cfg))

	return {
		"period": parse_period(config.get("Timer", "OnCalendar")),
		"delay": "0"
	}

def get_job(job_id):
	try:
		f = open(config_dir+"/"+job_id+".timer", "r")
	except OSError, e:
		return None

	cfg_str = f.read()
	f.close()
	cfg = parse_config(cfg_str)
	cfg["id"] = job_id
	return cfg

def write_config(config, config_file):
	f = tempfile.NamedTemporaryFile(delete=False)
	config.write(f)
	f.close()

	sudo_queue.append("mv "+f.name+" "+config_file)

def update_job(job):
	sudo_queue.reset()

	config_prefix = config_dir+"/"+job["id"]

	# Timer
	config = new_config()

	config.add_section("Unit")
	config.set("Unit", "Description", "Bups backup manager timer")

	config.add_section("Timer")
	config.set("Timer", "OnCalendar", "weekly") # TODO: support job["period"]
	config.set("Timer", "Persistent", "true") # Starts immediately if it missed the last start time

	config.add_section("Install")
	config.set("Install", "WantedBy", "timers.target")

	config_file = config_prefix+".timer"
	write_config(config, config_file)
	sudo_queue.append("chmod +r "+config_file)

	# Service
	config = new_config()

	config.add_section("Unit")
	config.set("Unit", "Description", "Bups backup manager service")

	config.add_section("Service")
	config.set("Service", "Type", "simple")
	config.set("Service", "ExecStart", job["command"])

	config_file = config_prefix+".service"
	write_config(config, config_file)
	sudo_queue.append("chmod +r "+config_file)

	sudo_queue.append("systemctl enable "+config_prefix+".timer")
	sudo_queue.append("systemctl start "+job["id"]+".timer")

	code = sudo_queue.execute()
	if code != 0:
		raise IOError("Could not update systemd job (process returned: "+str(code)+")")

def remove_job(job_id):
	sudo_queue.reset()

	sudo_queue.append("systemctl stop "+job_id+".timer")
	sudo_queue.append("systemctl disable "+job_id+".timer")
	sudo_queue.append("rm "+config_dir+"/"+job_id+".timer")
	sudo_queue.append("rm "+config_dir+"/"+job_id+".service")

	code = sudo_queue.execute()
	if code != 0:
		raise IOError("Could not delete systemd job (process returned: "+str(code)+")")