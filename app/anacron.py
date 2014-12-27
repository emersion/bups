import os
import subprocess
import tempfile

config_file = "/etc/anacrontab"

def is_available():
	return os.path.exists(config_file)

def parse_config_line(line):
	data = line.strip().split(None, 3)

	if len(data) == 0 or data[0].startswith('#'):
		return None
	if len(data) < 4:
		return None

	return {
		"period": data[0],
		"delay": data[1],
		"id": data[2],
		"command": data[3]
	}

def format_config_line(job):
	data = []
	for attr in ["period", "delay", "id", "command"]:
		data.append(str(job[attr]))

	return "\t".join(data)

def parse_config(anacrontab):
	cfg = []

	for line in anacrontab.split("\n"):
		data = parse_config_line(line)

		if data is None:
			continue

		cfg.append(data)

	return cfg

def read_config():
	f = open(config_file, 'r')
	cfg = parse_config(f.read())
	f.close()
	return cfg

def get_job(job_id):
	cfg = read_config()

	for job in cfg:
		if job["id"] == job_id:
			return job
	return None

def update_job(job, remove=False):
	f = open(config_file, 'r')
	lines = f.readlines()
	f.close()

	updated_line = None
	if not remove:
		updated_line = format_config_line(job)+"\n"

	i = 0
	updated = False
	for line in lines:
		data = parse_config_line(line)

		if data is not None and data["id"] == job["id"]:
			if remove:
				del lines[i]
			else:
				lines[i] = updated_line
			updated = True
			break # We updated the line, we can stop here

		i += 1

	if not updated and not remove:
		lines.append(updated_line)

	o = "".join(lines)

	f = tempfile.NamedTemporaryFile(delete=False)
	f.write(o)
	f.close()

	cmd = ["gksudo", "cp "+f.name+" "+config_file]
	code = subprocess.call(cmd)

	if code != 0:
		raise IOError("Could not write to "+config_file+" (process returned: "+str(code)+")")

	os.remove(f.name)

def remove_job(job_id):
	return update_job({ "id": job_id }, True)
