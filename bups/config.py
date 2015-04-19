import os
import json

sys_config_file = os.path.realpath(os.path.dirname(__file__)+"/config/config.json")
user_config_file = os.path.expanduser("~/.config/bups/config.json")

def file_path():
	if os.path.isfile(user_config_file):
		return user_config_file
	return sys_config_file

def read(custom_config_file=None):
	if custom_config_file is not None and os.path.isfile(custom_config_file):
		f = open(custom_config_file, 'r')
	else:
		f = open(file_path(), 'r')
	cfg = json.load(f)
	f.close()
	return cfg

def write(cfg):
	user_config_dir = os.path.dirname(user_config_file)
	if not os.path.exists(user_config_dir):
		os.makedirs(user_config_dir)
	f = open(user_config_file, 'w')

	json.dump(cfg, f, indent=4)
	f.close()
